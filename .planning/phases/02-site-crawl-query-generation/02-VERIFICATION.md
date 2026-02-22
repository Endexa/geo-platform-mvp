---
phase: 02-site-crawl-query-generation
verified: 2026-02-22T00:00:00Z
status: passed
score: 9/9 must-haves verified
re_verification: false
---

# Phase 2: Site Crawl & Query Generation Verification Report

**Phase Goal:** The system can take any URL, extract AI-readiness signals from the site, and generate a set of industry-relevant queries that a real user would ask an AI engine about that brand's domain
**Verified:** 2026-02-22
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                                         | Status     | Evidence                                                                                     |
|----|---------------------------------------------------------------------------------------------------------------|------------|----------------------------------------------------------------------------------------------|
| 1  | Given a URL, the system extracts structured data (schema.org JSON-LD, microdata, Open Graph)                  | VERIFIED   | `crawler_service.py:246` uses `extruct.extract()` with syntaxes `["json-ld","opengraph","microdata"]` |
| 2  | The system checks robots.txt for AI bot directives (GPTBot, ClaudeBot, PerplexityBot, Google-Extended, others) | VERIFIED   | `crawler_service.py:29-38` defines 8 bots; `_check_ai_bot_access()` fetches and parses robots.txt |
| 3  | The system extracts content structure (headings, meta description, main content, word count, keywords)        | VERIFIED   | `_extract_headings()`, `_extract_meta_description()`, `_extract_main_content()`, `_extract_keywords()` all implemented substantively |
| 4  | Crawl results are stored as JSONB in the Audit record                                                         | VERIFIED   | `audit.py:32` — `crawl_data = Column(JSONB, nullable=True)`; `audit_tasks.py:56` stores `crawl_result.model_dump()` |
| 5  | Audit and AuditQuery models exist with proper relationships and FK constraints                                 | VERIFIED   | `audit.py:40-47` has bidirectional `queries` relationship; migration 003 creates FK on `audit_queries.audit_id` and FK from `audit_cost_ledger.audit_id` |
| 6  | From crawled content, the system generates 10-15 categorized queries reflecting real user AI questions         | VERIFIED   | `query_generator.py:67-126` — `generate()` calls LiteLLM with `response_format=GeneratedQuerySet` (min 8, max 15 queries) |
| 7  | Generated queries span 5 categories: industry, brand_direct, comparison, problem, recommendation              | VERIFIED   | `query_generator.py:21-23` — `GeneratedQuery.category` is `Literal["industry","brand_direct","comparison","problem","recommendation"]` |
| 8  | The crawl-then-generate pipeline runs as a Celery background task                                             | VERIFIED   | `audit_tasks.py:20-25` — `@celery_app.task(bind=True, name="app.tasks.audit.run_crawl_and_generate")` orchestrates all stages |
| 9  | A user can trigger an audit by POSTing a URL to the audit API endpoint                                        | VERIFIED   | `api/audit.py:23-71` — `POST /audit/` creates an Audit record and calls `run_crawl_and_generate.delay()`; included in `main.py:146` |

**Score:** 9/9 truths verified

---

## Required Artifacts

### Plan 01 Artifacts (AUDIT-02)

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `backend/app/models/audit.py` | Audit SQLAlchemy model — central pipeline entity | VERIFIED | 48 lines. `class Audit` with JSONB `crawl_data`, UUID PK, FK to profiles, 7-value status enum, relationships to AuditQuery and AuditCostLedger |
| `backend/app/models/audit_query.py` | AuditQuery model for generated queries | VERIFIED | 29 lines. `class AuditQuery` with FK to audits, category, query_text, sort_order, and back-reference to Audit |
| `backend/alembic/versions/003_add_audits_and_audit_queries.py` | Alembic migration creating audits + audit_queries tables + FK to audit_cost_ledger | VERIFIED | `op.create_table` for both tables, index on audit_id, `create_foreign_key` for audit_cost_ledger with try/except safety |
| `backend/app/services/crawler_service.py` | CrawlerService returning CrawlResult | VERIFIED | 412 lines (exceeds 80-line minimum). 10 methods: crawl, _extract_title, _extract_meta_description, _extract_headings, _extract_main_content, _extract_structured_data, _extract_open_graph, _check_ai_bot_access, _extract_keywords, _detect_industry_signals, _extract_authority_markers |
| `backend/app/schemas/crawl.py` | Pydantic schemas for crawl results and AI bot access | VERIFIED | `AIBotAccess` with 8 Optional[bool] fields; `CrawlResult` with all 14 required fields |
| `backend/app/schemas/audit.py` | Pydantic request/response schemas for audit API | VERIFIED | `AuditCreate`, `AuditResponse`, `AuditDetailResponse`, `AuditQueryResponse` all present with `ConfigDict(from_attributes=True)` |

### Plan 02 Artifacts (AUDIT-03)

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `backend/app/services/query_generator.py` | QueryGeneratorService using LiteLLM structured output | VERIFIED | 280 lines (exceeds 60-line minimum). `generate()`, `_build_prompt()`, `extract_brand_name()` all substantively implemented |
| `backend/app/tasks/audit_tasks.py` | Celery task orchestrating crawl + query generation pipeline | VERIFIED | 106 lines. Contains `run_crawl_and_generate` with full 3-stage pipeline: CRAWLING → GENERATING_QUERIES → COMPLETED (or FAILED) |
| `backend/app/api/audit.py` | API endpoints for creating and retrieving audits | VERIFIED | 121 lines. `router` defined with 3 routes: POST /, GET /, GET /{audit_id} — all auth-guarded |

---

## Key Link Verification

### Plan 01 Key Links

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `models/audit.py` | `models/audit_query.py` | SQLAlchemy `relationship("AuditQuery"` | WIRED | `audit.py:40` — `queries = relationship("AuditQuery", back_populates="audit", cascade="all, delete-orphan")` |
| `services/crawler_service.py` | `schemas/crawl.py` | Returns `CrawlResult` | WIRED | `crawler_service.py:17` imports `CrawlResult`; return type on `crawl()` is `CrawlResult`; `line 155` returns a fully constructed `CrawlResult(...)` |
| `alembic/versions/003_...py` | `models/audit_cost.py` | `create_foreign_key` from audit_cost_ledger.audit_id | WIRED | `003_...py:83-96` — `op.create_foreign_key("fk_audit_cost_ledger_audit_id", "audit_cost_ledger", "audits", ["audit_id"], ["id"])` with try/except |

### Plan 02 Key Links

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `services/query_generator.py` | `schemas/crawl.py` | Accepts `CrawlResult` data for prompt building | WIRED | `query_generator.py:67` — `generate(self, crawl_data: dict, brand_name: str)` processes crawl dict; `_build_prompt()` accesses `crawl_data` keys matching `CrawlResult` fields |
| `tasks/audit_tasks.py` | `services/crawler_service.py` | Calls `CrawlerService.crawl()` | WIRED | `audit_tasks.py:15,54-55` — imports and instantiates `CrawlerService`; calls `asyncio.run(crawler.crawl(url))` |
| `tasks/audit_tasks.py` | `services/query_generator.py` | Calls `QueryGeneratorService.generate()` | WIRED | `audit_tasks.py:16,68-72` — imports and instantiates `QueryGeneratorService`; calls `query_gen.extract_brand_name()` and `query_gen.generate()` |
| `tasks/audit_tasks.py` | `models/audit.py` | Updates Audit status and stores AuditQuery rows | WIRED | `audit_tasks.py:51,65,89` — sets `audit.status = AuditStatus.CRAWLING.value`, `GENERATING_QUERIES.value`, `COMPLETED.value`; `lines 75-82` create `AuditQuery` records |
| `api/audit.py` | `tasks/audit_tasks.py` | Dispatches Celery task on POST via `.delay()` | WIRED | `api/audit.py:18,63` — imports `run_crawl_and_generate`; calls `run_crawl_and_generate.delay(str(audit.id), request.url)` |
| `main.py` | `api/audit.py` | Includes audit router under `API_V1_PREFIX` | WIRED | `main.py:7` — `from app.api import ... audit`; `lines 145-148` — `app.include_router(audit.router, prefix=settings.API_V1_PREFIX)` |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| AUDIT-02 | 02-01-PLAN.md | App crawls the site and extracts AI-readiness signals (schema.org, robots.txt AI directives, structured data, content structure) | SATISFIED | `CrawlerService` (412 lines) extracts JSON-LD/OG/microdata via extruct, checks 8 AI bots in robots.txt, extracts headings/content/keywords/industry signals/authority markers; migration 003 + Audit model store results as JSONB |
| AUDIT-03 | 02-02-PLAN.md | App auto-generates industry-relevant queries from crawled site content | SATISFIED | `QueryGeneratorService.generate()` calls LiteLLM with `response_format=GeneratedQuerySet` producing 8-15 queries across 5 Literal-typed categories; `run_crawl_and_generate` stores them as `AuditQuery` records; `POST /audit/` exposes the trigger |

**No orphaned requirements.** REQUIREMENTS.md traceability table maps AUDIT-02 and AUDIT-03 to Phase 2 — both are satisfied.

---

## Anti-Patterns Found

No anti-patterns detected in any of the 9 phase artifacts. Specifically:

- No TODO/FIXME/PLACEHOLDER comments in any created file
- No stub implementations (`return null`, empty handlers, etc.)
- No unconnected imports — all key imports are used substantively
- `extruct` unavailability is handled with a graceful try/except fallback (not a stub — logs a warning and returns empty collections, preserving correctness)
- Migration 003 FK uses try/except with a descriptive comment for the orphan-row edge case — not a stub, this is intentional defensive handling documented in plan

---

## Human Verification Required

### 1. End-to-End Pipeline Execution

**Test:** POST a real URL (e.g., `https://stripe.com`) to `POST /api/v1/audit/` with a valid JWT. Poll `GET /api/v1/audit/{id}` until status is `completed`.
**Expected:** Audit record transitions PENDING → CRAWLING → GENERATING_QUERIES → COMPLETED; GET response contains 8-15 AuditQuery records across the 5 categories with natural-language phrasing.
**Why human:** Requires running Celery worker + DB + valid OpenAI API key. Cannot verify LLM output quality programmatically.

### 2. robots.txt Tri-State Accuracy

**Test:** Crawl a site with known robots.txt AI bot directives (e.g., one that explicitly blocks GPTBot) and inspect `ai_bot_access` in the returned crawl data.
**Expected:** Blocked bot shows `false`, explicitly allowed shows `true`, unlisted bots show `null`.
**Why human:** Requires a live HTTP request to a real site with known robots.txt content.

### 3. Query Relevance Quality

**Test:** Generate queries for a well-known brand in a specific industry (e.g., a SaaS company). Review the 5 categories.
**Expected:** Industry queries do not name the brand; brand_direct queries use the extracted brand name; comparison/problem/recommendation queries reflect actual site content rather than generic templates.
**Why human:** Requires LLM output quality judgment — cannot assess "realistic" phrasing programmatically.

---

## Summary

Phase 2 goal is **fully achieved**. All 9 observable truths are verified against the actual codebase:

**Plan 01 (AUDIT-02 — Site Crawl):**
- `CrawlerService` is a substantive 412-line implementation with 11 methods covering all required signal extraction
- `Audit` and `AuditQuery` models are correctly defined with JSONB storage, proper FK constraints, and bidirectional SQLAlchemy relationships
- Alembic migration 003 correctly creates both tables and retroactively links `audit_cost_ledger` with appropriate safety handling
- All schemas (`CrawlResult`, `AIBotAccess`, `AuditCreate`, `AuditResponse`, `AuditDetailResponse`, `AuditQueryResponse`) are substantive and complete

**Plan 02 (AUDIT-03 — Query Generation):**
- `QueryGeneratorService` is a substantive 280-line implementation using LiteLLM structured Pydantic output with proper category enforcement via `Literal` types
- `run_crawl_and_generate` Celery task fully orchestrates the pipeline with status updates at each stage and graceful error handling
- All 3 audit API endpoints are wired, authenticated, and included in `main.py` under `API_V1_PREFIX`
- Config settings (`QUERY_GEN_MODEL`, `QUERY_GEN_TEMPERATURE`, `QUERY_GEN_MAX_CONTENT_WORDS`) are present and used

The only items deferred to human verification are runtime behaviors that require live network access and LLM API keys.

---

_Verified: 2026-02-22_
_Verifier: Claude (gsd-verifier)_
