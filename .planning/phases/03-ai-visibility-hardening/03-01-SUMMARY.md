---
phase: 03-ai-visibility-hardening
plan: 01
subsystem: api, scoring
tags: [visibility, scoring, confidence, per-engine, alembic, pydantic]

# Dependency graph
requires:
  - phase: 01-scoring-foundation
    provides: VisibilityScore model, ScoringService, scoring pipeline
  - phase: 02-recommendations-competitor-benchmarking
    provides: ENGINE_CONFIG in dispatch_service, Alembic migration chain through 011
provides:
  - Enhanced VisibilityScore model with confidence_level, engines_queried, engines_skipped columns
  - Enriched per_engine_scores JSONB with statistical breakdown per engine
  - Weighted-by-queries-sent overall scoring algorithm (v2)
  - _compute_confidence_level static method for query count thresholds
  - PerEngineBreakdown Pydantic schema with display names
  - _build_per_engine_breakdown helper for old/new JSONB format compatibility
  - Alembic migration 012
affects: [03-02, frontend, dashboard, reports]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Enriched JSONB: store structured dicts in existing JSONB columns without schema migration"
    - "Backward-compatible serialization: getattr with defaults for pre-migration rows"
    - "Display name mapping: ENGINE_DISPLAY_NAMES constant for frontend-friendly engine labels"

key-files:
  created:
    - backend/alembic/versions/012_add_visibility_confidence_fields.py
  modified:
    - backend/app/models/visibility_score.py
    - backend/app/services/scoring_service.py
    - backend/app/schemas/audit.py
    - backend/app/api/audit.py

key-decisions:
  - "Weighted-by-queries-sent scoring: engines with more data points have proportionally more influence on overall score"
  - "Confidence thresholds: 0=not_measured, 1-4=low, 5-9=medium, 10+=high (no external dependencies)"
  - "Enriched JSONB coexistence: old integer format and new dict format live in same per_engine_scores column"

patterns-established:
  - "JSONB enrichment: add structured data to existing JSONB without schema migration"
  - "Backward-compatible API: getattr with defaults for gradual rollout"

requirements-completed: [VIS-01, VIS-02, VIS-03, VIS-04]

# Metrics
duration: 5min
completed: 2026-02-26
---

# Phase 3 Plan 01: Enhanced Visibility Scoring Pipeline Summary

**Enriched per-engine visibility scoring with weighted averaging, confidence indicators, skipped-engine reporting, and backward-compatible API serialization**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-26T07:43:41Z
- **Completed:** 2026-02-26T07:48:52Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments
- VisibilityScore model extended with confidence_level, engines_queried, engines_skipped columns (Alembic migration 012)
- ScoringService switched to weighted-by-queries-sent averaging with enriched per-engine breakdown including queries_sent, queries_with_mentions, mention_rate, total_mentions, avg_confidence, confidence_level, and skipped flag
- Skipped engines (no API key) automatically included in breakdown with skip_reason
- API schemas extended with PerEngineBreakdown model and ENGINE_DISPLAY_NAMES (ChatGPT, Claude, Perplexity, Gemini)
- Audit endpoint builds per_engine_breakdown from both old integer and new dict JSONB formats

## Task Commits

Each task was committed atomically:

1. **Task 1: Enhance VisibilityScore model and create Alembic migration** - `6c53a96c` (feat)
2. **Task 2: Enhance ScoringService with per-engine statistical breakdown** - `b10c716f` (feat)
3. **Task 3: Enhance API schemas and audit endpoint for per-engine breakdown** - `2b41831b` (feat)

## Files Created/Modified
- `backend/app/models/visibility_score.py` - Added confidence_level, engines_queried, engines_skipped columns; bumped default to v2
- `backend/alembic/versions/012_add_visibility_confidence_fields.py` - Migration adding 3 new columns with server_defaults
- `backend/app/services/scoring_service.py` - Enriched per-engine breakdown, weighted scoring, confidence levels, skipped engines
- `backend/app/schemas/audit.py` - PerEngineBreakdown model, ENGINE_DISPLAY_NAMES, extended VisibilityScoreSchema
- `backend/app/api/audit.py` - _build_per_engine_breakdown helper, enriched visibility_score serialization

## Decisions Made
- Weighted-by-queries-sent scoring instead of equal-weight averaging -- engines with more data should have proportionally more influence
- Simple threshold-based confidence levels (0/1-4/5-9/10+) -- no scipy or statistical interval needed
- Enriched JSONB coexistence -- old {"openai": 75} and new {"openai": {...}} formats share the same column via schema-less JSONB

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Pre-existing test_get_audit_detail and test_dashboard failures (500 errors) were already failing before Phase 3 changes -- not a regression. All 23 scoring pipeline tests pass.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Backend scoring pipeline complete with enriched data
- Ready for Plan 03-02: frontend confidence badges and comprehensive test suite
- per_engine_breakdown data structure is stable and documented

---
*Phase: 03-ai-visibility-hardening*
*Completed: 2026-02-26*
