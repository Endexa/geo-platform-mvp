---
phase: 04-mention-detection-scoring
plan: 01
subsystem: api
tags: [rapidfuzz, sqlalchemy, mention-detection, visibility-scoring, nlp, regex]

# Dependency graph
requires:
  - phase: 03-ai-engine-dispatch
    provides: EngineResponse model with response_text for brand detection
provides:
  - BrandMention model with FK to engine_responses
  - VisibilityScore model with FK to audits and JSONB per-engine breakdown
  - MentionDetectorService with layered exact + fuzzy detection
  - ScoringService with weighted 0-100 visibility computation
  - Migration 005 for brand_mentions and visibility_scores tables
affects: [04-02-pipeline-integration, phase-05-report-generation]

# Tech tracking
tech-stack:
  added: [rapidfuzz>=3.14.0]
  patterns: [layered-detection (exact-then-fuzzy), weighted-scoring-formula, brand-variant-generation]

key-files:
  created:
    - backend/app/models/brand_mention.py
    - backend/app/models/visibility_score.py
    - backend/alembic/versions/005_add_brand_mentions_and_visibility_scores.py
    - backend/app/services/mention_detector.py
    - backend/app/services/scoring_service.py
  modified:
    - backend/app/models/__init__.py
    - backend/alembic/env.py
    - backend/app/core/config.py
    - backend/requirements.txt

key-decisions:
  - "Deduplication by exact offset match, not 50-char window -- prevents collapsing legitimate separate mentions"
  - "Short brand names (<4 chars) use case-sensitive matching to avoid false positives (e.g., 'Go' vs 'go')"
  - "Fuzzy pass requires both token_set_ratio AND partial_ratio above threshold for dual validation"

patterns-established:
  - "Layered detection: exact regex first, fuzzy RapidFuzz fallback only when no exact matches found"
  - "Brand variant generation: suffix-stripped, abbreviation, domain-style -- algorithmically from brand name"
  - "Scoring formula: 40% mention rate, 30% position, 30% prominence -- clamped to 0-100"
  - "Algorithm versioning: ScoringService.ALGORITHM_VERSION tracks formula version for reproducibility"

requirements-completed: [AUDIT-05, AUDIT-06]

# Metrics
duration: 4min
completed: 2026-02-22
---

# Phase 4 Plan 01: Mention Detection & Scoring Models and Services Summary

**BrandMention/VisibilityScore models with layered exact+fuzzy MentionDetectorService (rapidfuzz) and weighted 0-100 ScoringService**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-22T02:20:38Z
- **Completed:** 2026-02-22T02:25:02Z
- **Tasks:** 3
- **Files modified:** 9

## Accomplishments
- BrandMention and VisibilityScore SQLAlchemy models with FKs, indexes, and Alembic migration 005
- MentionDetectorService with two-pass detection (exact regex + RapidFuzz fuzzy), brand variant generation, verbatim context extraction, and deduplication
- ScoringService with weighted formula (40% mention rate, 30% position, 30% prominence), per-engine breakdown, error response filtering, and algorithm versioning

## Task Commits

Each task was committed atomically:

1. **Task 1: Create BrandMention and VisibilityScore models, migration 005, config settings, and add rapidfuzz dependency** - `25ffe734` (feat)
2. **Task 2: Create MentionDetectorService with layered exact + fuzzy detection** - `6be1e3c6` (feat)
3. **Task 3: Create ScoringService with weighted visibility score computation** - `c377b158` (feat)

## Files Created/Modified
- `backend/app/models/brand_mention.py` - BrandMention model with FK to engine_responses, match_type, confidence, context_quote
- `backend/app/models/visibility_score.py` - VisibilityScore model with FK to audits, JSONB per_engine_scores, algorithm_version
- `backend/alembic/versions/005_add_brand_mentions_and_visibility_scores.py` - Migration 005 creating both tables
- `backend/app/services/mention_detector.py` - MentionDetectorService (289 lines) with layered detection
- `backend/app/services/scoring_service.py` - ScoringService (181 lines) with weighted scoring formula
- `backend/app/models/__init__.py` - Added BrandMention, VisibilityScore imports
- `backend/alembic/env.py` - Added model imports for metadata population
- `backend/app/core/config.py` - Added MENTION_FUZZY_THRESHOLD, MENTION_SHORT_NAME_THRESHOLD, MENTION_CONTEXT_WINDOW_CHARS
- `backend/requirements.txt` - Added rapidfuzz>=3.14.0

## Decisions Made
- **Deduplication by exact offset:** Changed from 50-char window overlap to exact offset deduplication to prevent collapsing legitimate separate mentions of the same brand at different positions
- **Case-sensitive short names:** Brand names shorter than 4 characters use case-sensitive regex matching to avoid false positives (e.g., "Go" should not match "go" in normal text)
- **Dual fuzzy threshold:** Fuzzy pass requires BOTH token_set_ratio AND partial_ratio to exceed threshold, reducing false positive rate

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed deduplication collapsing separate mentions**
- **Found during:** Task 2 (MentionDetectorService)
- **Issue:** Original 50-char window dedup was collapsing two legitimate "Acme" mentions at offset 0 and 36 into one
- **Fix:** Changed to exact offset deduplication with separate overlap handling for fuzzy-vs-exact conflicts
- **Files modified:** backend/app/services/mention_detector.py
- **Verification:** Test shows 2 mentions detected for "Acme is a great company. They offer Acme products."
- **Committed in:** 6be1e3c6 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix)
**Impact on plan:** Essential correctness fix for deduplication logic. No scope creep.

## Issues Encountered
None beyond the deduplication fix documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Models and services ready for Plan 02 pipeline integration
- MentionDetectorService and ScoringService are stateless (except DB session for scoring) -- ready for Celery task wrapping
- rapidfuzz dependency must be installed in Docker image (added to requirements.txt)

## Self-Check: PASSED

All 5 created files exist. All 3 task commits verified (25ffe734, 6be1e3c6, c377b158).

---
*Phase: 04-mention-detection-scoring*
*Completed: 2026-02-22*
