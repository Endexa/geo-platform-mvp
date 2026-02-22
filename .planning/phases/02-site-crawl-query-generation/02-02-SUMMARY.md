---
phase: 02-site-crawl-query-generation
plan: 02
subsystem: services, api, tasks
tags: [litellm, pydantic, celery, structured-output, query-generation, fastapi]

# Dependency graph
requires:
  - phase: 02-site-crawl-query-generation
    plan: 01
    provides: "Audit/AuditQuery models, CrawlerService, CrawlResult schema, Alembic migration 003"
provides:
  - "QueryGeneratorService with LiteLLM structured Pydantic output for categorized queries"
  - "Celery audit pipeline task (crawl -> extract brand -> generate queries -> store)"
  - "POST /api/v1/audit/ endpoint for triggering audits"
  - "GET /api/v1/audit/{id} endpoint for audit details with queries"
  - "GET /api/v1/audit/ endpoint for listing user audits"
affects: [03-ai-query-dispatch, 04-scoring-engine, 05-api-frontend]

# Tech tracking
tech-stack:
  added: []
  patterns: [LiteLLM structured output with Pydantic response_format, Celery task pipeline with status updates, brand name extraction priority chain]

key-files:
  created:
    - backend/app/services/query_generator.py
    - backend/app/tasks/audit_tasks.py
    - backend/app/api/audit.py
  modified:
    - backend/app/core/config.py
    - backend/app/main.py

key-decisions:
  - "QueryGeneratorService.generate() is synchronous (litellm.completion is sync by default) -- no async issues in Celery"
  - "Brand name extraction uses 4-level priority: schema.org Organization > og:site_name > title tag first segment > domain name"
  - "Audit status set to COMPLETED after query generation (Phase 3 will change flow to continue to DISPATCHING)"
  - "LLM prompt includes headings, keywords, schema types, OG data, and truncated main content for optimal query generation context"
  - "GeneratedQuery category enforced via Literal type (not plain str) for compile-time and runtime validation"

patterns-established:
  - "LiteLLM structured output: response_format=PydanticModel for typed LLM responses"
  - "Celery audit pipeline: status updates at each stage (PENDING -> CRAWLING -> GENERATING_QUERIES -> COMPLETED)"
  - "Audit API pattern: POST returns 202 Accepted, GET polls for status/results"
  - "Owner-only access: all audit endpoints verify user_id matches current_user.id"

requirements-completed: [AUDIT-03]

# Metrics
duration: 4min
completed: 2026-02-22
---

# Phase 2 Plan 2: Site Crawl & Query Generation - LLM Query Generation and Audit Pipeline Summary

**QueryGeneratorService using LiteLLM structured Pydantic output for 10-15 categorized brand visibility queries, wired through Celery pipeline and REST API**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-22T01:08:50Z
- **Completed:** 2026-02-22T01:12:26Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- QueryGeneratorService with LiteLLM structured output producing 10-15 categorized queries across 5 categories (industry, brand_direct, comparison, problem, recommendation)
- Brand name extraction with 4-level priority chain: schema.org Organization > OG site_name > title tag > domain fallback
- Celery task `run_crawl_and_generate` orchestrating full audit pipeline with status updates at each stage
- Three audit API endpoints (POST create, GET detail with queries, GET list with pagination) all requiring JWT auth

## Task Commits

Each task was committed atomically:

1. **Task 1: Create QueryGeneratorService with LiteLLM structured output and config settings** - `04d21eba` (feat)
2. **Task 2: Create Celery audit pipeline task and API endpoint for triggering audits** - `284f061e` (feat)

## Files Created/Modified
- `backend/app/services/query_generator.py` - QueryGeneratorService (280 lines) with generate(), _build_prompt(), extract_brand_name()
- `backend/app/tasks/audit_tasks.py` - Celery task run_crawl_and_generate with full pipeline orchestration
- `backend/app/api/audit.py` - Audit API router with POST, GET detail, GET list endpoints
- `backend/app/core/config.py` - Added QUERY_GEN_MODEL, QUERY_GEN_TEMPERATURE, QUERY_GEN_MAX_CONTENT_WORDS settings
- `backend/app/main.py` - Included audit router under API_V1_PREFIX

## Decisions Made
- QueryGeneratorService.generate() is synchronous -- litellm.completion() is sync by default, safe to call directly in Celery workers
- Brand name extraction uses 4-level priority chain for robustness across different site configurations
- Audit status set to COMPLETED after query generation since Phase 3 is not yet built (Phase 3 will extend the pipeline to DISPATCHING)
- GeneratedQuery uses Literal type for category validation rather than plain str, catching invalid categories at parse time
- LLM prompt truncates main content to QUERY_GEN_MAX_CONTENT_WORDS (2000) to keep token usage reasonable

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required. QUERY_GEN_MODEL defaults to gpt-4o (requires OPENAI_API_KEY already configured in Phase 1).

## Next Phase Readiness
- Complete Phase 2 pipeline ready: POST URL -> crawl -> generate queries -> store results
- AuditQuery records ready for Phase 3 (AI Engine Dispatch) to consume
- Audit status progression ready for Phase 3 to extend (GENERATING_QUERIES -> DISPATCHING)
- API endpoints ready for Phase 5 (frontend) to integrate with

## Self-Check: PASSED

- All 3 created files verified present on disk
- Both task commits (04d21eba, 284f061e) verified in git log

---
*Phase: 02-site-crawl-query-generation*
*Completed: 2026-02-22*
