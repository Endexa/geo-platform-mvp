---
phase: 04-mention-detection-scoring
plan: 02
subsystem: api
tags: [celery, pipeline, pydantic, eager-loading, sqlalchemy, visibility-score, brand-mentions]

# Dependency graph
requires:
  - phase: 04-mention-detection-scoring
    plan: 01
    provides: MentionDetectorService, ScoringService, BrandMention model, VisibilityScore model
  - phase: 03-ai-engine-dispatch
    provides: EngineResponse model, DispatchService, Celery audit pipeline stages 1-3
provides:
  - ANALYZING stage in Celery pipeline (stage 4 between DISPATCHING and COMPLETED)
  - BrandMentionSchema and VisibilityScoreSchema Pydantic schemas
  - Audit detail API returning mentions nested under engine responses
  - Audit detail API returning visibility score with per-engine breakdown
  - Eager loading for mentions and visibility_score joins
affects: [phase-05-report-generation, frontend-audit-detail]

# Tech tracking
tech-stack:
  added: []
  patterns: [5-stage-celery-pipeline, eager-load-nested-mentions, backref-list-handling]

key-files:
  created: []
  modified:
    - backend/app/tasks/audit_tasks.py
    - backend/app/schemas/audit.py
    - backend/app/api/audit.py

key-decisions:
  - "QueryGeneratorService instantiated in Stage 4 for brand name re-extraction (instance method, not static)"
  - "Backref visibility_score handled as list with isinstance check for forward-compatible access"
  - "ANALYZING status added to dispatch_summary computation filter"

patterns-established:
  - "5-stage pipeline: CRAWLING -> GENERATING_QUERIES -> DISPATCHING -> ANALYZING -> COMPLETED"
  - "Nested eager loading: Audit -> queries -> engine_responses -> mentions (3-level join)"
  - "Backref list handling: audit.visibility_score accessed as list[0] with isinstance guard"

requirements-completed: [AUDIT-05, AUDIT-06]

# Metrics
duration: 2min
completed: 2026-02-22
---

# Phase 4 Plan 02: Pipeline Integration & API Schema Extension Summary

**ANALYZING stage in Celery pipeline wiring MentionDetectorService + ScoringService, with extended audit detail API returning mentions and visibility scores**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-22T02:28:14Z
- **Completed:** 2026-02-22T02:30:44Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Celery audit pipeline extended to 5 stages with ANALYZING between DISPATCHING and COMPLETED
- Brand mentions detected and stored for every successful engine response during ANALYZING stage
- Visibility score computed and stored after all mentions detected
- Audit detail API returns BrandMentionSchema nested under EngineResponseSchema and VisibilityScoreSchema at audit level
- Eager loading prevents N+1 queries with 3-level join (queries -> engine_responses -> mentions)

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend Celery pipeline with ANALYZING stage for mention detection and scoring** - `3f936861` (feat)
2. **Task 2: Extend audit schemas and API to expose mention data and visibility scores** - `a958933b` (feat)

## Files Created/Modified
- `backend/app/tasks/audit_tasks.py` - Added Stage 4 (ANALYZING) with MentionDetectorService and ScoringService wiring
- `backend/app/schemas/audit.py` - Added BrandMentionSchema, VisibilityScoreSchema, mentions on EngineResponseSchema, visibility_score on AuditDetailResponse
- `backend/app/api/audit.py` - Extended eager loading with EngineResponse.mentions and Audit.visibility_score, added visibility_score to response

## Decisions Made
- **QueryGeneratorService instantiation:** Plan called `QueryGeneratorService.extract_brand_name()` as a class method, but it is an instance method. Instantiated `QueryGeneratorService()` in Stage 4 for brand name re-extraction from crawl_data.
- **Backref list handling:** `Audit.visibility_score` backref returns a list by default. Used `isinstance(vs, list)` guard to access `vs[0]` safely, forward-compatible if relationship changes to `uselist=False`.
- **ANALYZING in dispatch summary filter:** Added `AuditStatus.ANALYZING.value` to the status check for computing dispatch_summary, since the audit may be polled during analysis.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed QueryGeneratorService.extract_brand_name call**
- **Found during:** Task 1 (ANALYZING stage implementation)
- **Issue:** Plan specified `QueryGeneratorService.extract_brand_name(audit.crawl_data)` as a class/static method call, but it is an instance method requiring instantiation
- **Fix:** Changed to `QueryGeneratorService().extract_brand_name(audit.crawl_data)` with instance creation
- **Files modified:** backend/app/tasks/audit_tasks.py
- **Verification:** `from app.tasks.audit_tasks import run_crawl_and_generate` imports without error
- **Committed in:** 3f936861 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix)
**Impact on plan:** Essential correctness fix for method call. No scope creep.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- End-to-end pipeline is now complete: URL -> crawl -> generate queries -> dispatch to AI engines -> detect mentions -> compute score -> return scored results
- Phase 4 fully complete (both plans executed)
- Ready for Phase 5 (report generation) which can consume the visibility score and mention data from the API

## Self-Check: PASSED

All 3 modified files exist. Both task commits verified (3f936861, a958933b).

---
*Phase: 04-mention-detection-scoring*
*Completed: 2026-02-22*
