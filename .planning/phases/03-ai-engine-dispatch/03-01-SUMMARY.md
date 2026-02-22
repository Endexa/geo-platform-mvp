---
phase: 03-ai-engine-dispatch
plan: 01
subsystem: api
tags: [litellm, sqlalchemy, threadpoolexecutor, redis-cache, rate-limiter, cost-tracking]

# Dependency graph
requires:
  - phase: 01-foundation-safety
    provides: "AICacheService, outbound rate limiter, CostTrackingService, AuditCostLedger"
  - phase: 02-site-crawl-query-generation
    provides: "AuditQuery model, Audit model with status states"
provides:
  - "EngineResponse SQLAlchemy model for storing AI engine responses"
  - "Migration 004 creating engine_responses table"
  - "DispatchService for parallel 3-engine query dispatch with cache/limiter/cost integration"
  - "DispatchResult dataclass for dispatch outcome tracking"
  - "Dispatch config settings (models, temperature, timeout, workers, Perplexity surcharge)"
affects: [03-02, 04-response-analysis, 05-scoring]

# Tech tracking
tech-stack:
  added: [litellm]
  patterns: [ThreadPoolExecutor-per-query, thread-local-db-sessions, asyncio-event-loop-per-thread]

key-files:
  created:
    - backend/app/models/engine_response.py
    - backend/alembic/versions/004_add_engine_responses.py
    - backend/app/services/dispatch_service.py
  modified:
    - backend/app/models/__init__.py
    - backend/app/models/audit_query.py
    - backend/alembic/env.py
    - backend/app/core/config.py

key-decisions:
  - "Thread-local DB sessions in ThreadPoolExecutor (SQLAlchemy sessions are not thread-safe)"
  - "Thread-local asyncio event loops for async cache and rate limiter calls from sync threads"
  - "API key validation before engine call — skip with error message if missing, not crash"
  - "Perplexity surcharge added post-call since LiteLLM does not track Perplexity search fees"

patterns-established:
  - "ThreadPoolExecutor parallel dispatch: one executor per query, all engines in parallel"
  - "Graceful degradation: engine failure produces EngineResponse with error_message, not exception"
  - "Budget gating: check_budget() before each query batch, stop dispatch if exceeded"
  - "Cache-before-dispatch: check AICacheService before rate limiter acquire and API call"

requirements-completed: [AUDIT-04]

# Metrics
duration: 3min
completed: 2026-02-22
---

# Phase 3 Plan 01: Engine Response Model & Dispatch Service Summary

**EngineResponse model with migration 004, DispatchService with ThreadPoolExecutor parallel 3-engine dispatch integrating AICacheService, rate limiter, and CostTrackingService**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-22T01:38:52Z
- **Completed:** 2026-02-22T01:41:38Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- EngineResponse SQLAlchemy model stores full AI response text, model version, token counts, cost, cached flag, error message, and timestamp per engine
- DispatchService dispatches queries to OpenAI, Anthropic, and Perplexity in parallel via ThreadPoolExecutor with budget checks, cache integration, rate limiting, and cost tracking
- Migration 004 creates engine_responses table with FK to audit_queries and indexed audit_query_id
- Dispatch config settings: 3 configurable engine models, temperature, timeout, max workers, Perplexity surcharge

## Task Commits

Each task was committed atomically:

1. **Task 1: Create EngineResponse model, migration 004, and dispatch config settings** - `6bd61a8c` (feat)
2. **Task 2: Create DispatchService with parallel engine dispatch** - `cb649aee` (feat)

## Files Created/Modified
- `backend/app/models/engine_response.py` - EngineResponse SQLAlchemy model with all response metadata columns
- `backend/alembic/versions/004_add_engine_responses.py` - Migration creating engine_responses table
- `backend/app/services/dispatch_service.py` - DispatchService with parallel dispatch, cache, rate limiting, cost tracking (368 lines)
- `backend/app/models/__init__.py` - Added EngineResponse export
- `backend/app/models/audit_query.py` - Added engine_responses relationship with cascade delete
- `backend/alembic/env.py` - Added EngineResponse import for autogenerate
- `backend/app/core/config.py` - Added dispatch settings (models, temperature, timeout, workers, surcharge)

## Decisions Made
- Thread-local DB sessions: each ThreadPoolExecutor thread creates its own SessionLocal() since SQLAlchemy sessions are not thread-safe
- Thread-local asyncio event loops: each thread creates asyncio.new_event_loop() for async cache/limiter calls, closed in finally
- API key validation before engine call: missing keys produce error EngineResponse instead of crashing
- Perplexity surcharge: added after LiteLLM cost calculation since LiteLLM does not track Perplexity per-request search fees

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required. API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY, PERPLEXITYAI_API_KEY) are validated at runtime with graceful error handling if missing.

## Next Phase Readiness
- EngineResponse model and DispatchService ready for Plan 02 (Celery task integration, API endpoints, dispatch pipeline)
- All Phase 1 infrastructure (cache, rate limiter, cost tracking) successfully integrated
- Budget gating and graceful degradation patterns established for production use

## Self-Check: PASSED

All 3 created files verified on disk. Both task commits (6bd61a8c, cb649aee) verified in git log.

---
*Phase: 03-ai-engine-dispatch*
*Completed: 2026-02-22*
