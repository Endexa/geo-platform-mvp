---
phase: 06-site-ai-readiness-scoring
plan: 01
subsystem: scoring
tags: [sqlalchemy, celery, scoring, multi-page-crawl, weakest-link-aggregation, abc]

# Dependency graph
requires:
  - phase: 04-mention-detection-scoring
    provides: VisibilityScore model and ScoringService for visibility computation
  - phase: 02-site-crawl-query-generation
    provides: CrawlerService for page fetching and CrawlResult schema
provides:
  - PageScore and CriterionResult models for storing per-page and per-criterion scores
  - BaseScorer ABC defining the contract for all category scorers
  - ScoringOrchestrator coordinating multi-page crawl, scoring, and aggregation
  - CrawlerService.crawl_multiple() for concurrent multi-page crawling
  - SCORING stage in the Celery audit pipeline
  - Migration 006 creating page_scores and criterion_results tables
affects: [06-02, 06-03, 06-04, 06-05, 07-auto-competitor, 09-dashboard]

# Tech tracking
tech-stack:
  added: []
  patterns: [BaseScorer ABC for category scorers, ScoringCriterionResult dataclass, weakest-link aggregation, conditional scorer imports]

key-files:
  created:
    - backend/app/models/page_score.py
    - backend/app/models/criterion_result.py
    - backend/app/services/scoring/__init__.py
    - backend/app/services/scoring/base_scorer.py
    - backend/app/services/scoring/scoring_orchestrator.py
    - backend/alembic/versions/006_add_page_scores_and_criterion_results.py
  modified:
    - backend/app/models/__init__.py
    - backend/app/models/audit.py
    - backend/app/services/crawler_service.py
    - backend/app/core/config.py
    - backend/app/tasks/audit_tasks.py
    - backend/app/schemas/audit.py
    - backend/alembic/env.py
    - docs/progression.md

key-decisions:
  - "Weakest-link aggregation: 0.6 * mean + 0.4 * min across pages penalizes inconsistency"
  - "Conditional scorer imports allow pipeline to work with 0-4 scorers registered"
  - "ScoringCriterionResult is a dataclass distinct from CriterionResult SQLAlchemy model"
  - "SKIP_URL_PATTERNS excludes login, admin, assets, static files from discovery"

patterns-established:
  - "BaseScorer ABC: all category scorers inherit and implement score_page() -> list[ScoringCriterionResult]"
  - "Conditional import pattern: try/except ImportError for incremental scorer registration"
  - "Weakest-link aggregation: 60% mean + 40% min for cross-page score combination"
  - "compute_category_score excludes checked=False criteria from averaging"

requirements-completed: [READY-05, READY-06]

# Metrics
duration: 5min
completed: 2026-02-22
---

# Phase 6 Plan 01: Scoring Pipeline Foundation Summary

**PageScore/CriterionResult DB models, BaseScorer ABC, ScoringOrchestrator with weakest-link aggregation, and SCORING Celery stage for multi-page site scoring**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-22T16:37:18Z
- **Completed:** 2026-02-22T16:42:30Z
- **Tasks:** 2
- **Files modified:** 14

## Accomplishments
- PageScore and CriterionResult SQLAlchemy models with full column specs, relationships, and migration 006
- BaseScorer ABC defining score_page()/compute_category_score() contract for all 4 category scorers
- ScoringOrchestrator with internal link discovery, multi-page crawl, per-page scoring, DB persistence, and weakest-link aggregation
- CrawlerService.crawl_multiple() for concurrent multi-page crawling with graceful degradation
- SCORING stage wired into the Celery pipeline between ANALYZING and COMPLETED with conditional scorer imports
- Config settings: SCORING_CRAWL_CAP (25), SCORING_STAGE_TIMEOUT_SECONDS (600), GOOGLE_API_KEY

## Task Commits

Each task was committed atomically:

1. **Task 1: Create PageScore and CriterionResult models with migration 006** - `5db88132` (feat)
2. **Task 2: Create BaseScorer, ScoringOrchestrator, multi-page crawl, SCORING stage** - `aebd6f21` (feat)

## Files Created/Modified
- `backend/app/models/page_score.py` - PageScore model with per-category scores and discovery metadata
- `backend/app/models/criterion_result.py` - CriterionResult model for per-criterion score storage
- `backend/app/services/scoring/__init__.py` - Package exports for scoring module
- `backend/app/services/scoring/base_scorer.py` - BaseScorer ABC and ScoringCriterionResult dataclass
- `backend/app/services/scoring/scoring_orchestrator.py` - Multi-page crawl, scoring coordination, weakest-link aggregation
- `backend/alembic/versions/006_add_page_scores_and_criterion_results.py` - Migration creating both tables and adding optimization_score to audits
- `backend/app/models/__init__.py` - Added PageScore, CriterionResult to package exports
- `backend/app/models/audit.py` - Added AuditStatus.SCORING and optimization_score column
- `backend/app/services/crawler_service.py` - Added crawl_multiple() method
- `backend/app/core/config.py` - Added SCORING_CRAWL_CAP, SCORING_STAGE_TIMEOUT_SECONDS, GOOGLE_API_KEY
- `backend/app/tasks/audit_tasks.py` - Added SCORING stage with conditional scorer imports
- `backend/app/schemas/audit.py` - Added optimization_score to AuditDetailResponse
- `backend/alembic/env.py` - Added PageScore, CriterionResult model imports

## Decisions Made
- **Weakest-link aggregation formula:** `0.6 * mean + 0.4 * min` across pages -- penalizes sites with inconsistent page quality rather than averaging away problems
- **Conditional scorer imports:** try/except ImportError blocks for each of the 4 category scorers, allowing the pipeline to run with 0 scorers registered (graceful before Plans 02-05 are built)
- **Separate dataclass vs ORM model:** ScoringCriterionResult (dataclass) is the in-memory return type used by scorers; CriterionResult (SQLAlchemy model) is for DB persistence. This separation keeps scorers independent of the ORM.
- **URL discovery filtering:** SKIP_URL_PATTERNS regex excludes login, signup, admin, API, assets, static, and binary files from internal link discovery

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Plans 02-05 can now build category scorers inheriting BaseScorer and registering with ScoringOrchestrator
- The SCORING stage will produce optimization_score=0 until scorers are registered (graceful degradation)
- All DB models and migration ready for immediate use

---
*Phase: 06-site-ai-readiness-scoring*
*Completed: 2026-02-22*
