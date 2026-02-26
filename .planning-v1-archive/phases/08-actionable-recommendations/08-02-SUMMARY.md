---
phase: 08-actionable-recommendations
plan: 02
subsystem: backend, api
tags: [recommendation-api, content-gaps, markdown-export, sentiment-api, fastapi, pydantic]

# Dependency graph
requires:
  - phase: 08-actionable-recommendations/01
    provides: AuditRecommendation model, RecommendationEngine service, SentimentService, MentionSentiment model
  - phase: 07-auto-competitor-discovery
    provides: DiscoveredCompetitor.queries_mentioned_in for content gap detection
provides:
  - Recommendation API with 5 endpoints (list, status update, sentiment, content gaps, markdown export)
  - Content gap identification cross-referencing user vs competitor mentions per query
  - Template-based mini briefs for content gaps
  - Markdown fix plan export with GSD-inspired format
  - 6 Pydantic schemas for recommendation responses
affects: [08-03, 09-dashboard-reporting]

# Tech tracking
tech-stack:
  added: []
  patterns: [content-gap-cross-reference, markdown-export-dynamic, audit-ownership-403]

key-files:
  created:
    - backend/app/api/recommendations.py
    - backend/app/schemas/recommendation.py
  modified:
    - backend/app/services/recommendation_engine.py
    - backend/app/main.py

key-decisions:
  - "Content gaps use deterministic query cross-reference (no LLM): compare user brand mentions vs competitor mentions per AuditQuery"
  - "Template-based mini briefs (zero cost, instant) with 5 research-backed key points per gap"
  - "Markdown export generates dynamically from DB on each request (no file storage)"
  - "Recommendation list returns unfiltered progress stats (done/dismissed/open counts) alongside filtered results"
  - "Audit ownership returns 403 Forbidden (not 404) when user_id mismatch, matching security best practice"

patterns-established:
  - "Content gap identification: cross-reference AuditQuery set against DiscoveredCompetitor.queries_mentioned_in"
  - "Markdown export: GSD-inspired fix plan with evidence, steps, code snippets, and acceptance criteria"
  - "API ownership pattern: _verify_audit_ownership helper returning 404/403"

requirements-completed: [REC-01, REC-02, REC-03, REC-04, REC-05]

# Metrics
duration: 3min
completed: 2026-02-23
---

# Phase 8 Plan 02: Recommendation API + Content Gaps + Markdown Export Summary

**5-endpoint recommendation API with content gap identification, per-engine sentiment summary, and GSD-inspired Markdown fix plan export**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-22T23:03:27Z
- **Completed:** 2026-02-22T23:06:43Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Content gap identification method cross-references user brand mentions against competitor entity mentions per query, producing gaps with template-based mini briefs
- Markdown export generates structured fix plans (grouped by page and priority) with evidence, action steps, code snippets, and acceptance criteria
- 5 API endpoints: recommendation list (with filtering), status PATCH, sentiment summary, content gaps, and Markdown export download
- 6 Pydantic schemas with Literal validation on status updates (only open/done/dismissed accepted)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add content gap identification to RecommendationEngine and create Pydantic schemas** - `c1ec07a9` (feat)
2. **Task 2: Create recommendation API endpoints and wire router** - `c70aa1c5` (feat)

## Files Created/Modified
- `backend/app/schemas/recommendation.py` - 6 Pydantic schemas: AuditRecommendationResponse, RecommendationStatusUpdate, RecommendationListResponse, SentimentSummaryResponse, ContentGapResponse, ContentGapListResponse
- `backend/app/api/recommendations.py` - 5 endpoints: GET list, PATCH status, GET sentiment, GET content-gaps, GET export/markdown
- `backend/app/services/recommendation_engine.py` - Added identify_content_gaps(), save_content_gaps(), _template_brief(), export_markdown(), _append_priority_groups()
- `backend/app/main.py` - Added recommendations router import and include_router()

## Decisions Made
- Content gaps use deterministic query cross-reference (no LLM cost) comparing user brand mentions vs competitor mentions per AuditQuery
- Template-based mini briefs generate 5 research-backed key points per gap (stats, FAQPage, citations, E-E-A-T, competitor coverage)
- Markdown export generates dynamically from DB on each request -- no file storage needed
- Recommendation list endpoint returns unfiltered progress stats (done/dismissed/open totals) alongside filtered results for accurate progress tracking
- Audit ownership verification returns 403 Forbidden when user_id mismatch (distinguishing from 404 Not Found for missing audits)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required. All endpoints use existing auth and database infrastructure.

## Next Phase Readiness
- Recommendation API fully functional and auth-protected, ready for frontend consumption (08-03)
- Content gaps populated at audit completion via save_content_gaps() (called from Celery pipeline)
- Markdown export endpoint returns proper Content-Disposition headers for browser download
- All response schemas validated with from_attributes=True for ORM compatibility

## Self-Check: PASSED

All created files verified present. All commit hashes verified in git log.

---
*Phase: 08-actionable-recommendations*
*Completed: 2026-02-23*
