---
phase: 07-auto-competitor-discovery
plan: 02
subsystem: backend, api, services
tags: [competitor-crawling, url-resolution, leaderboard, scoring-pipeline, httpx, rapidfuzz]

# Dependency graph
requires:
  - phase: 07-auto-competitor-discovery
    provides: "DiscoveredCompetitor and CompetitorAudit models, EntityExtractorService, DISCOVERING_COMPETITORS pipeline stage"
  - phase: 06-site-ai-readiness-scoring
    provides: "ScoringOrchestrator, BaseScorer, 4 category scorers for page-level scoring"
provides:
  - "CompetitorService with URL resolution, crawl+score, and leaderboard methods"
  - "Competitor API endpoints: GET leaderboard, POST crawl, GET competitor detail"
  - "Pydantic schemas: CompetitorLeaderboardEntry, CompetitorAuditSummary, CompetitorLeaderboardResponse"
  - "Auto-competitor crawling wired into DISCOVERING_COMPETITORS pipeline stage"
affects: [07-03, 07-04, 08-recommendations]

# Tech tracking
tech-stack:
  added: []
  patterns: [layered-url-resolution, non-fatal-competitor-crawling, per-category-scoring-averages]

key-files:
  created:
    - backend/app/services/competitor_service.py
    - backend/app/schemas/competitor.py
    - backend/app/api/competitors.py
  modified:
    - backend/app/tasks/audit_tasks.py
    - backend/app/main.py

key-decisions:
  - "Layered URL resolution: citation URL > domain heuristic > Knowledge Graph API (graceful degradation)"
  - "Competitor pages scored directly via individual scorers, NOT via ScoringOrchestrator.score_audit() -- avoids creating PageScore/CriterionResult DB records for competitors"
  - "Competitor crawling is non-fatal in audit pipeline -- try/except wrapping ensures audit completes even if competitor crawl fails"
  - "Sequential competitor crawling (not parallel) to avoid rate limiting external sites"
  - "Competitor crawl endpoint is synchronous (not Celery) since 3-5 competitors take ~30-60s"

patterns-established:
  - "Layered URL resolution: try citation matching, then domain heuristic, then Knowledge Graph API"
  - "Non-fatal pipeline extension: wrap optional stages in try/except to prevent audit failure"
  - "Competitor scoring via direct scorer invocation: build scorers, run score_page, compute averages"

requirements-completed: [COMP-03, COMP-04]

# Metrics
duration: 5min
completed: 2026-02-22
---

# Phase 7 Plan 02: Competitor Crawl & Leaderboard API Summary

**CompetitorService with layered URL resolution (citation/heuristic/KG), crawler+scorer pipeline reusing Phase 6 scorers, and 3-endpoint competitor API with SOV leaderboard**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-22T21:35:12Z
- **Completed:** 2026-02-22T21:40:08Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- CompetitorService resolving brand names to URLs via layered strategy (citation URL matching > domain heuristic > Google Knowledge Graph)
- Competitor sites crawled and scored using all 4 Phase 6 category scorers, per-category averages stored on CompetitorAudit
- 3 competitor API endpoints: leaderboard (GET), trigger crawl (POST), competitor detail (GET) -- all auth-protected with audit ownership verification
- DISCOVERING_COMPETITORS pipeline stage now extracts entities AND crawls top competitors, with non-fatal error handling

## Task Commits

Each task was committed atomically:

1. **Task 1: Create CompetitorService with URL resolution and competitor crawl+score pipeline** - `92171368` (feat)
2. **Task 2: Create competitor API endpoints and wire competitor crawling into audit pipeline** - `43695d57` (feat)

## Files Created/Modified
- `backend/app/services/competitor_service.py` - CompetitorService with resolve_competitor_url, crawl_and_score_competitor, crawl_top_competitors, get_leaderboard
- `backend/app/schemas/competitor.py` - Pydantic schemas: CompetitorLeaderboardEntry, CompetitorAuditSummary, CompetitorLeaderboardResponse
- `backend/app/api/competitors.py` - 3 API endpoints: leaderboard, crawl trigger, competitor detail
- `backend/app/tasks/audit_tasks.py` - Added CompetitorService crawl_top_competitors call in DISCOVERING_COMPETITORS stage
- `backend/app/main.py` - Registered competitors router

## Decisions Made
- **Layered URL resolution:** Citation URL matching (rapidfuzz partial_ratio > 70) tried first as highest-quality signal, domain heuristic second, Knowledge Graph API third. Each layer degrades gracefully.
- **Direct scorer invocation:** Competitors scored via individual BaseScorer.score_page() calls, not ScoringOrchestrator.score_audit(). This avoids creating PageScore/CriterionResult DB records for competitors, keeping the data model clean.
- **Non-fatal pipeline integration:** Competitor crawling wrapped in try/except with separate asyncio event loop. Audit completes even if all competitor crawls fail.
- **Sequential crawling:** Competitors crawled one-at-a-time to avoid rate limiting external sites. Can be parallelized later if needed.
- **Synchronous crawl endpoint:** The POST /crawl endpoint runs directly (not via Celery) since 3-5 competitors take ~30-60s. Can be moved to Celery if latency becomes an issue.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. Google Knowledge Graph API (optional) uses the existing GOOGLE_API_KEY setting from Phase 6.

## Next Phase Readiness
- CompetitorService complete, ready for Plan 03 (comparison views and competitive gap analysis)
- Leaderboard API ready for frontend integration in Plan 04
- CompetitorAudit records with per-category averages ready for comparative scoring

## Self-Check: PASSED

All files verified present. All commits verified in git log.

---
*Phase: 07-auto-competitor-discovery*
*Completed: 2026-02-22*
