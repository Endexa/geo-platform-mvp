---
phase: 03-ai-engine-dispatch
verified: 2026-02-22T00:00:00Z
status: passed
score: 12/12 must-haves verified
re_verification: false
gaps: []
human_verification:
  - test: "Trigger a real audit with valid API keys and confirm all three engines return responses"
    expected: "EngineResponse records created for openai, anthropic, and perplexity with non-empty response_text"
    why_human: "Requires live API keys, running Celery worker, and a reachable PostgreSQL + Redis stack"
  - test: "Trigger a real audit with one invalid API key (e.g. blank ANTHROPIC_API_KEY)"
    expected: "The other two engines complete normally; the failing engine produces an EngineResponse with error_message set and response_text empty"
    why_human: "Graceful degradation requires a live run to confirm isolation at the ThreadPoolExecutor boundary"
  - test: "Trigger an audit that would exceed the $1.00 budget mid-dispatch"
    expected: "Dispatch stops after the budget-exceeded query; audit reaches COMPLETED with budget_exceeded=true in logs"
    why_human: "Budget gating depends on cumulative DB state that cannot be faked with static analysis"
---

# Phase 3: AI Engine Dispatch — Verification Report

**Phase Goal:** The system can send generated queries to ChatGPT, Claude, and Perplexity in parallel and store their responses reliably, with graceful degradation if one engine fails
**Verified:** 2026-02-22
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (Plan 01)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | EngineResponse model can store full AI response text, model version, token counts, cost, and timestamp for each engine | VERIFIED | `backend/app/models/engine_response.py` has all columns: `response_text` (Text), `model_version` (String), `prompt_tokens` (Integer), `completion_tokens` (Integer), `cost_usd` (Numeric 10,6), `created_at` (DateTime tz-aware), plus `cached` and `error_message` |
| 2 | DispatchService dispatches a single query to all three engines in parallel using ThreadPoolExecutor | VERIFIED | `_dispatch_query_to_engines()` in `dispatch_service.py` lines 120-158 creates a `ThreadPoolExecutor(max_workers=settings.DISPATCH_MAX_WORKERS)` and submits `_call_engine` for all three ENGINE_CONFIG entries simultaneously using `as_completed()` |
| 3 | A single engine failure does not prevent other engines from returning results (graceful degradation) | VERIFIED | Lines 148-156: each future is wrapped in `try/except`; exceptions create an error `EngineResponse` via `_create_error_response()` rather than propagating. `_call_engine` itself also has a top-level `except` (lines 316-334) that creates and persists an error response |
| 4 | Cached responses are served from AICacheService for duplicate query+engine combinations | VERIFIED | Lines 192-223: `cache.get()` called before rate limiter acquire; on cache hit, an `EngineResponse` with `cached=True` and `cost_usd=Decimal("0")` is created and persisted without making an API call |
| 5 | Rate limiters are acquired before each engine call and released in finally blocks | VERIFIED | Line 229: `loop.run_until_complete(limiter.acquire())`. Lines 311-314: `finally: limiter.release()` wraps the entire LiteLLM call block |
| 6 | Cost is recorded via CostTrackingService after each successful engine call | VERIFIED | Lines 277-284: `CostTrackingService(thread_db).record_cost(...)` called with audit_id, engine, model_version, tokens, and `cost_decimal`. Also called for cached responses (zero-cost entry, lines 213-221) |
| 7 | Budget is checked before each query dispatch batch and dispatch stops if exceeded | VERIFIED | Lines 87-93: `CostTrackingService(self.db).check_budget(audit_id)` called before each query iteration; `budget_exceeded = True` and `break` on failure |

### Observable Truths (Plan 02)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 8 | Celery audit pipeline continues from query generation into dispatch stage (GENERATING_QUERIES -> DISPATCHING -> COMPLETED) | VERIFIED | `audit_tasks.py` lines 97-123: sets `AuditStatus.DISPATCHING.value`, commits, then calls `DispatchService.dispatch_all_queries()`, then sets `AuditStatus.COMPLETED.value` |
| 9 | Audit status shows DISPATCHING while engine queries are running | VERIFIED | Line 99: `audit.status = AuditStatus.DISPATCHING.value` committed (line 100) before `DispatchService` is invoked |
| 10 | GET /api/v1/audit/{id} returns engine responses nested under each query | VERIFIED | `audit.py` line 118: `joinedload(Audit.queries).joinedload(AuditQuery.engine_responses)`; `AuditDetailResponse` serialises `queries: list[AuditQueryResponse]` where each has `engine_responses: list[EngineResponseSchema]` |
| 11 | Dispatch failures set audit to FAILED with error message, not stuck in DISPATCHING | VERIFIED | `audit_tasks.py` lines 125-135: outer `except Exception` sets `audit.status = AuditStatus.FAILED.value` and `audit.error_message = str(e)[:1000]`. Existing error handler wraps the entire pipeline |
| 12 | Audit marked COMPLETED only after dispatch finishes (not after query generation) | VERIFIED | Lines 119-123: `AuditStatus.COMPLETED.value` only set after `dispatch_all_queries()` returns successfully |

**Score:** 12/12 truths verified

---

## Required Artifacts

### Plan 01 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/models/engine_response.py` | EngineResponse SQLAlchemy model | VERIFIED | 35 lines, `class EngineResponse(Base)` with all 11 columns including FK, relationship, and timezone-aware timestamp |
| `backend/alembic/versions/004_add_engine_responses.py` | Migration creating engine_responses table | VERIFIED | `op.create_table("engine_responses", ...)` with all columns matching model; `op.create_index("ix_engine_responses_audit_query_id",...)`; proper downgrade |
| `backend/app/services/dispatch_service.py` | DispatchService with parallel dispatch, cache, rate limiting, cost tracking | VERIFIED | 369 lines (exceeds 100-line minimum); substantive implementation with `DispatchService`, `DispatchResult`, `ENGINE_CONFIG`, `_dispatch_query_to_engines`, `_call_engine`, `_create_error_response` |

### Plan 02 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/tasks/audit_tasks.py` | Extended Celery pipeline with Stage 3 dispatch | VERIFIED | Contains `from app.services.dispatch_service import DispatchService`, `AuditStatus.DISPATCHING.value`, and `dispatcher.dispatch_all_queries()` call |
| `backend/app/schemas/audit.py` | EngineResponseSchema and updated AuditDetailResponse | VERIFIED | `EngineResponseSchema` (10 fields), `DispatchSummary`, `AuditQueryResponse` with `engine_responses: list[EngineResponseSchema] = []`, `AuditDetailResponse` with `dispatch_summary: Optional[DispatchSummary] = None` |
| `backend/app/api/audit.py` | Audit detail endpoint returning engine responses | VERIFIED | `get_audit` endpoint uses `joinedload(Audit.queries).joinedload(AuditQuery.engine_responses)`, computes `dispatch_summary`, and returns `AuditDetailResponse.model_validate(audit)` |

### Supporting Modified Files

| File | Expected Change | Status | Details |
|------|----------------|--------|---------|
| `backend/app/models/__init__.py` | Export EngineResponse | VERIFIED | Line 10: `from app.models.engine_response import EngineResponse`; line 25: `"EngineResponse"` in `__all__` |
| `backend/app/models/audit_query.py` | engine_responses relationship | VERIFIED | Lines 30-32: `engine_responses = relationship("EngineResponse", back_populates="audit_query", cascade="all, delete-orphan")` |
| `backend/alembic/env.py` | EngineResponse import for autogenerate | VERIFIED | Line 22: `from app.models.engine_response import EngineResponse  # noqa: F401` |
| `backend/app/core/config.py` | Dispatch settings section | VERIFIED | Lines 112-120: All 8 settings present: `PERPLEXITYAI_API_KEY`, `DISPATCH_MODEL_OPENAI`, `DISPATCH_MODEL_ANTHROPIC`, `DISPATCH_MODEL_PERPLEXITY`, `DISPATCH_TEMPERATURE=0.0`, `DISPATCH_TIMEOUT_SECONDS=60`, `DISPATCH_MAX_WORKERS=6`, `PERPLEXITY_REQUEST_SURCHARGE=0.005` |

---

## Key Link Verification

### Plan 01 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `dispatch_service.py` | `cache_service.py` | `AICacheService.get()` and `.set()` | WIRED | Line 187: `cache = AICacheService()`. Lines 192-196: `loop.run_until_complete(cache.get(...))`. Lines 264-272: `loop.run_until_complete(cache.set(...))` |
| `dispatch_service.py` | `outbound_limiter.py` | `get_provider_limiter()` acquire/release | WIRED | Line 28: `from app.core.outbound_limiter import get_provider_limiter`. Line 188: `limiter = get_provider_limiter(config["provider"])`. Line 229: `loop.run_until_complete(limiter.acquire())`. Line 313: `limiter.release()` in `finally` |
| `dispatch_service.py` | `cost_service.py` | `CostTrackingService.record_cost()` and `.check_budget()` | WIRED | Line 32: `from app.services.cost_service import CostTrackingService`. Line 87: `CostTrackingService(self.db).check_budget(audit_id)`. Lines 213, 277: `CostTrackingService(thread_db).record_cost(...)` |
| `dispatch_service.py` | `engine_response.py` | Creating EngineResponse records for each engine result | WIRED | Line 30: `from app.models.engine_response import EngineResponse`. EngineResponse instantiated at lines 198, 291, 321, 353 — all paths persist via `thread_db.add()` and `thread_db.commit()` |

### Plan 02 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `audit_tasks.py` | `dispatch_service.py` | `DispatchService(db).dispatch_all_queries()` | WIRED | Line 23: `from app.services.dispatch_service import DispatchService`. Line 105: `dispatcher = DispatchService(db)`. Line 106: `dispatcher.dispatch_all_queries(audit_id=audit_id, queries=queries)` |
| `audit_tasks.py` | `audit.py` (model) | `AuditStatus.DISPATCHING` status update | WIRED | Line 19: `from app.models.audit import Audit, AuditStatus`. Line 99: `audit.status = AuditStatus.DISPATCHING.value` |
| `schemas/audit.py` | `engine_response.py` | `EngineResponseSchema` mirrors EngineResponse model | WIRED | `EngineResponseSchema` in `schemas/audit.py` has `model_config = ConfigDict(from_attributes=True)` and mirrors all 10 EngineResponse model columns. `AuditQueryResponse.engine_responses: list[EngineResponseSchema] = []` |

---

## Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| AUDIT-04 | 03-01-PLAN, 03-02-PLAN | App queries ChatGPT, Claude, and Perplexity APIs with generated queries | SATISFIED | `DispatchService._call_engine()` calls `litellm.completion(model=model, ...)` where model is drawn from `DISPATCH_MODEL_OPENAI`, `DISPATCH_MODEL_ANTHROPIC`, and `DISPATCH_MODEL_PERPLEXITY`. All three are dispatched in parallel via `ThreadPoolExecutor`. Responses stored in `engine_responses` table via `EngineResponse` model. |

No orphaned requirements found. AUDIT-04 is the only requirement mapped to Phase 3 in REQUIREMENTS.md (line 99), and both plans claim it.

---

## Anti-Pattern Scan

Files scanned: `engine_response.py`, `dispatch_service.py`, `004_add_engine_responses.py`, `audit_tasks.py`, `schemas/audit.py`, `api/audit.py`

| File | Pattern | Severity | Finding |
|------|---------|----------|---------|
| All files | TODO/FIXME/placeholder | — | None found |
| All files | Empty implementations (`return null`, `return {}`, stub handlers) | — | None found |
| `dispatch_service.py` | Console.log-only implementations | — | None found; loguru used correctly |

No anti-patterns detected.

---

## Human Verification Required

### 1. Live Three-Engine Dispatch

**Test:** With valid `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, and `PERPLEXITYAI_API_KEY` set, trigger an audit via `POST /api/v1/audit/`, wait for status COMPLETED, then `GET /api/v1/audit/{id}`.

**Expected:** Response contains `queries[*].engine_responses` with three entries per query — one for `openai`, one for `anthropic`, one for `perplexity` — each with non-empty `response_text`, non-null `model_version`, and `error_message: null`.

**Why human:** Requires live API keys, running Celery worker, running Redis, and a reachable PostgreSQL instance.

### 2. Graceful Degradation Under One Engine Failure

**Test:** Set `ANTHROPIC_API_KEY=""` (blank), trigger an audit, wait for COMPLETED.

**Expected:** `GET /api/v1/audit/{id}` returns two successful engine responses (openai + perplexity) and one error response (anthropic) with `error_message: "API key not configured for anthropic"` and `response_text: ""`. Audit status must be COMPLETED, not FAILED.

**Why human:** Requires live stack. The code path for API key missing (`_call_engine` lines 173-180) creates an error EngineResponse and returns it — it does not raise. The outer `_dispatch_query_to_engines` collects it. Static analysis confirms the logic but only a live run proves the thread isolation works end-to-end.

### 3. Budget Gating Under Cost Accumulation

**Test:** Set `AUDIT_BUDGET_USD=0.001` (fraction of a cent), trigger an audit with multiple queries.

**Expected:** Dispatch stops after the first or second query (depending on actual cost); remaining queries receive no engine responses. Audit reaches COMPLETED with a log line `"Budget exceeded for audit ... Stopping dispatch."`. `dispatch_summary.total_queries` will be less than the total query count.

**Why human:** Budget gating depends on cumulative `AuditCostLedger` DB state from previous calls, which cannot be simulated via static analysis.

---

## Gaps Summary

No gaps. All 12 observable truths are verified, all artifacts are substantive and wired, all key links are confirmed, and AUDIT-04 is fully satisfied. The three items above require human verification against a live stack but do not represent implementation gaps — the code paths exist and are correct.

---

_Verified: 2026-02-22_
_Verifier: Claude (gsd-verifier)_
