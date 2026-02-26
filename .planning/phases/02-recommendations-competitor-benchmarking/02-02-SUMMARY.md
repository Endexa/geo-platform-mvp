---
phase: 02-recommendations-competitor-benchmarking
plan: 02
subsystem: api, database
tags: [sqlalchemy, alembic, rapidfuzz, competitor-persistence, brand-linking, sov-trend, score-comparison]

# Dependency graph
requires:
  - phase: 01-scoring-foundation
    provides: PageScore model with per-category scores, optimization_score on Audit
provides:
  - Brand.is_competitor boolean for distinguishing competitor vs user brands
  - DiscoveredCompetitor.competitor_brand_id FK linking competitors to persistent Brand entities
  - CompetitorService.link_competitor_to_brand with 4-level matching strategy
  - CompetitorService.link_audit_competitors_to_brands batch linking method
  - CompetitorService.get_competitor_sov_trend time-series SOV query
  - CompetitorService.get_score_comparison site-vs-competitor score comparison
  - GET /competitors/brands/{brand_id}/sov-trend endpoint
  - GET /competitors/{audit_id}/score-comparison endpoint
  - ScoreComparisonResponse Pydantic schema
  - Alembic migration 011 for new columns and index
affects: [02-03, dashboard, frontend]

# Tech tracking
tech-stack:
  added: []
  patterns: [multi-level brand matching (domain > name > fuzzy > create), per-user competitor isolation]

key-files:
  created:
    - backend/alembic/versions/011_add_competitor_brand_linking.py
    - backend/tests/test_competitor_persistence.py
  modified:
    - backend/app/models/brand.py
    - backend/app/models/competitor.py
    - backend/app/services/competitor_service.py
    - backend/app/api/competitors.py
    - backend/app/schemas/competitor.py

key-decisions:
  - "Brand linking uses 4-level priority: domain match > exact name > fuzzy name (>90 token_set_ratio) > create new"
  - "SOV trend query joins DiscoveredCompetitor with Audit to get audit dates, ordered ascending"
  - "Score comparison reads site category scores from PageScore averages, not a JSONB field"
  - "Alembic migration chained as 011 (after existing 010 from plan 02-01)"

patterns-established:
  - "Per-user competitor brand isolation: all Brand queries filter by user_id to prevent cross-user leakage"
  - "Static method pattern for queries not requiring instance state (get_competitor_sov_trend)"

requirements-completed: [COMP-01, COMP-02, COMP-03, COMP-04]

# Metrics
duration: 8min
completed: 2026-02-26
---

# Phase 2 Plan 2: Cross-Audit Competitor Persistence Summary

**4-level brand matching (domain > name > fuzzy > create) linking DiscoveredCompetitor to Brand for SOV trending and side-by-side score comparison**

## Performance

- **Duration:** 8 min
- **Started:** 2026-02-26T04:51:14Z
- **Completed:** 2026-02-26T04:59:40Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments
- DiscoveredCompetitor records now link to Brand entities via competitor_brand_id FK, enabling cross-audit tracking
- Brand linking uses 4-level matching: domain match (strongest signal), exact name, fuzzy name (rapidfuzz >90), or create new Brand
- SOV trend endpoint returns time-series share-of-voice data for a competitor brand across multiple audits
- Score comparison endpoint returns user's site optimization and per-category scores alongside each completed competitor
- Per-user isolation ensures two users discovering the same competitor get independent Brand records
- 9 new tests all passing, full suite 105 tests with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Add Brand linking schema and migration** - `88d4c2f1` (feat)
2. **Task 2: Implement brand linking logic, SOV trend query, and API endpoint** - `35677ca6` (feat)
3. **Task 3: Add side-by-side score comparison endpoint** - `d9301185` (feat)

## Files Created/Modified
- `backend/app/models/brand.py` - Added `is_competitor` Boolean column
- `backend/app/models/competitor.py` - Added `competitor_brand_id` FK and `competitor_brand` relationship
- `backend/alembic/versions/011_add_competitor_brand_linking.py` - Migration adding is_competitor and competitor_brand_id columns with index
- `backend/app/services/competitor_service.py` - Added link_competitor_to_brand, link_audit_competitors_to_brands, get_competitor_sov_trend, get_score_comparison
- `backend/app/api/competitors.py` - Added GET /brands/{brand_id}/sov-trend and GET /{audit_id}/score-comparison endpoints
- `backend/app/schemas/competitor.py` - Added ScoreComparisonSite, ScoreComparisonCompetitor, ScoreComparisonResponse schemas
- `backend/tests/test_competitor_persistence.py` - 9 tests covering brand linking, per-user isolation, SOV trending, and score comparison

## Decisions Made
- Brand linking uses domain match as strongest signal (resolved_url domain extraction), falling through to exact name, fuzzy match (>90 threshold), then creating a new competitor Brand
- SOV trend query joins DiscoveredCompetitor with Audit table to get audit dates -- ordered ascending for time-series display
- Score comparison reads site per-category scores from PageScore model averages rather than a JSONB field on Audit (consistent with how the scoring pipeline stores results)
- Migration numbered 011 to chain after existing migration 010 from plan 02-01

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed migration numbering conflict with plan 02-01**
- **Found during:** Task 2 (running migration)
- **Issue:** Plan specified migration file 011 but I initially created it as 010, which collided with an existing 010_add_vertical_and_score_delta.py from plan 02-01
- **Fix:** Renamed to 011, updated revision ID to "011" and down_revision to "010"
- **Files modified:** backend/alembic/versions/011_add_competitor_brand_linking.py
- **Verification:** `alembic upgrade head` succeeded, both 010 and 011 applied
- **Committed in:** 35677ca6 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Migration renumbering was necessary to avoid Alembic head conflict. No scope creep.

## Issues Encountered
None beyond the migration numbering resolved above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Brand linking infrastructure is ready for plan 02-03 to wire into audit_tasks.py (call link_audit_competitors_to_brands after competitor discovery)
- SOV trend and score comparison endpoints are operational and accessible via authenticated API calls
- All models, migrations, and tests are in place

## Self-Check: PASSED

All 7 key files verified present. All 3 task commit hashes verified in git log. 105/105 tests passing.

---
*Phase: 02-recommendations-competitor-benchmarking*
*Completed: 2026-02-26*
