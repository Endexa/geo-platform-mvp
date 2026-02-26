---
phase: 02-recommendations-competitor-benchmarking
plan: 01
subsystem: api, database
tags: [vertical-classifier, recommendation-engine, schema-org, impact-delta, alembic]

# Dependency graph
requires:
  - phase: 01-scoring-foundation
    provides: scoring pipeline with 61 criteria across 4 categories (C, CS, SD, A/S)
provides:
  - VerticalClassifier service detecting 6 site verticals from crawl data
  - Vertical-aware recommendation filtering via VERTICAL_EXCLUSIONS
  - Impact delta calculation for each recommendation
  - Alembic migration 010 adding vertical and estimated_score_delta columns
affects: [02-02, 02-03, audit-pipeline-wiring, recommendation-api, recommendation-export]

# Tech tracking
tech-stack:
  added: []
  patterns: [heuristic-classifier-with-priority-fallback, vertical-exclusion-filter, linear-impact-estimation]

key-files:
  created:
    - backend/app/services/vertical_classifier.py
    - backend/alembic/versions/010_add_vertical_and_score_delta.py
    - backend/tests/test_vertical_classifier.py
    - backend/tests/test_recommendation_enhancements.py
  modified:
    - backend/app/models/audit.py
    - backend/app/models/audit_recommendation.py
    - backend/app/services/recommendation_engine.py

key-decisions:
  - "Vertical exclusions use actual criterion IDs (SD8=Product, SD10=ClaimReview) not research placeholders"
  - "Impact delta formula uses linear estimate (score_improvement / num_criteria * weight) with 0.8 multi-page conservative multiplier and 15-point cap"
  - "ECOMMERCE content signals include 'price' which can match SaaS pricing pages -- acceptable ambiguity since schema.org types are the primary signal"

patterns-established:
  - "Heuristic classifier pattern: 3-priority fallback (schema > content > fallback) returning enum value"
  - "Vertical exclusion pattern: dict mapping vertical -> set of excluded criterion_ids, checked with is_recommendation_relevant()"
  - "Impact delta pattern: category_weight * (score_gap / num_criteria), capped at 15, adjusted for multi-page"

requirements-completed: [REC-01, REC-02, REC-03, REC-04, REC-05]

# Metrics
duration: 6min
completed: 2026-02-26
---

# Phase 2 Plan 01: Vertical Classifier + Recommendation Enhancements Summary

**Heuristic vertical classifier detecting 6 site types from schema.org and crawl signals, wired into recommendation engine with vertical-aware filtering and per-criterion impact delta estimates**

## Performance

- **Duration:** 6 min
- **Started:** 2026-02-26T04:51:08Z
- **Completed:** 2026-02-26T04:58:04Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- VerticalClassifier correctly classifies SaaS, e-commerce, local business, media/blog, B2B, and generic verticals from schema.org @type signals with URL/content fallback
- Recommendation engine filters out irrelevant schema recommendations per vertical (SD8 Product excluded for SaaS, SD10 ClaimReview excluded for SaaS/ecommerce/local_business)
- Each recommendation now includes estimated_score_delta showing approximate optimization score improvement if fixed
- Alembic migration 010 adds both new columns (audits.vertical, audit_recommendations.estimated_score_delta) with nullable for backward compatibility
- 37 new tests (21 classifier + 16 recommendation enhancements) plus 105 total passing with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Create VerticalClassifier service and Alembic migration** - `2d844ddc` (feat)
2. **Task 2: Enhance recommendation engine with vertical filtering and impact delta** - `07a552ef` (feat)

## Files Created/Modified
- `backend/app/services/vertical_classifier.py` - SiteVertical enum + VerticalClassifier with 3-priority heuristic detection
- `backend/app/services/recommendation_engine.py` - VERTICAL_EXCLUSIONS, is_recommendation_relevant(), _compute_impact_delta(), vertical parameter on generate_recommendations()
- `backend/app/models/audit.py` - Added vertical column (String, nullable)
- `backend/app/models/audit_recommendation.py` - Added estimated_score_delta column (Numeric(4,1), nullable)
- `backend/alembic/versions/010_add_vertical_and_score_delta.py` - Migration adding both columns
- `backend/tests/test_vertical_classifier.py` - 21 tests covering all 6 verticals, priority ordering, schema extraction
- `backend/tests/test_recommendation_enhancements.py` - 16 tests: relevance filter, impact delta bounds, DB integration

## Decisions Made
- Used actual criterion IDs from structured_data_scorer.py (SD8=Product/Offer, SD10=ClaimReview) instead of research placeholder IDs (SD3_LocalBusiness). The research used hypothetical IDs; the real codebase has SD1-SD13 mapped to specific schema types.
- Impact delta uses simplified linear estimation rather than full scoring re-simulation. Per research: "Computing exact impact deltas with full scoring re-simulation would be slow and complex. The linear estimation is sufficiently accurate for user-facing estimates."
- Kept FAQPage (SD3), Organization (SD1), Article (SD4), and JSON-LD (SD7) as universally relevant -- these are applicable to all verticals.
- Content pattern matching ("price", "product" in HTML) can produce false positives for SaaS sites, but schema.org types take priority and resolve ambiguity for well-structured sites. Generic fallback ensures no filtering for ambiguous cases.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed PageScore constructor in integration tests**
- **Found during:** Task 2 (integration test setup)
- **Issue:** Test used `optimization_score` which doesn't exist on PageScore model (correct field is `overall_page_score`)
- **Fix:** Changed test fixture to use `overall_page_score=40`
- **Files modified:** backend/tests/test_recommendation_enhancements.py
- **Verification:** Both integration tests pass against real Supabase DB
- **Committed in:** 07a552ef (Task 2 commit)

**2. [Rule 3 - Blocking] Remapped criterion IDs from research to actual codebase IDs**
- **Found during:** Task 2 (VERTICAL_EXCLUSIONS setup)
- **Issue:** Research used placeholder IDs like SD3_LocalBusiness, SD3_Product, SD3_ClaimReview. Actual codebase uses SD1-SD13 where SD8=Product/Offer and SD10=ClaimReview. There is no LocalBusiness criterion at all.
- **Fix:** Mapped exclusions to real IDs: SD8 (Product/Offer) and SD10 (ClaimReview)
- **Files modified:** backend/app/services/recommendation_engine.py
- **Verification:** is_recommendation_relevant() tests pass with real IDs
- **Committed in:** 07a552ef (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** Both fixes necessary for correctness. No scope creep.

## Issues Encountered
None beyond the auto-fixed deviations.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Vertical classifier is ready to be wired into the audit pipeline (audit_tasks.py Stage 1 -> classify -> store on Audit)
- generate_recommendations() now accepts vertical parameter -- needs to be called with audit.vertical in Stage 7
- Impact deltas need frontend display integration in RecommendationCard component
- Cross-audit competitor persistence (02-03) can build on this foundation

## Self-Check: PASSED

All 7 created/modified files exist on disk. Both task commits (2d844ddc, 07a552ef) verified in git log. 105 tests passing, zero regressions.

---
*Phase: 02-recommendations-competitor-benchmarking*
*Completed: 2026-02-26*
