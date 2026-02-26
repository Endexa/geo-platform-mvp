---
phase: 08-actionable-recommendations
plan: 03
subsystem: frontend, ui
tags: [vue-components, recommendations-ui, sentiment-breakdown, content-gaps, markdown-export, nuxt-page, tailwind]

# Dependency graph
requires:
  - phase: 08-actionable-recommendations/02
    provides: Recommendation API endpoints (list, status PATCH, sentiment, content gaps, markdown export)
  - phase: 08-actionable-recommendations/01
    provides: AuditRecommendation model, RecommendationEngine service, SentimentService
  - phase: 05-audit-experience
    provides: Audit page, dashboard layout, useApiFetch composable
provides:
  - RecommendationCard component with two-tier expand/collapse (summary + action steps + code snippets)
  - RecommendationProgress bar with per-priority remaining counts
  - SentimentBreakdown per-engine grid with color-coded dominant sentiment
  - ContentGapCard topic cards with expandable mini briefs
  - Full /recommendations page with 4 tabs (By Priority, By Page, Content Gaps, Sentiment)
  - Markdown fix plan export from recommendations page
  - Recommendation preview on audit page (progress bar + top 5 high-priority)
  - Sidebar navigation with Recommendations item
affects: [09-dashboard-reporting]

# Tech tracking
tech-stack:
  added: []
  patterns: [two-tier-card-expand, optimistic-status-update, parallel-api-loading, tab-with-filters]

key-files:
  created:
    - frontend/components/RecommendationCard.vue
    - frontend/components/RecommendationProgress.vue
    - frontend/components/SentimentBreakdown.vue
    - frontend/components/ContentGapCard.vue
    - frontend/pages/recommendations.vue
  modified:
    - frontend/pages/audit.vue
    - frontend/layouts/dashboard.vue

key-decisions:
  - "Replaced Optimization nav item with Recommendations (same LightBulbIcon) since recommendations IS the optimization experience"
  - "Optimistic status updates with rollback on PATCH error for responsive UX"
  - "Sentiment and content gaps fetched with .catch(() => null) for fail-silent loading"
  - "Page groups auto-expanded on initial load for discoverability"
  - "Recommendation preview limited to top 5 high-priority open items on audit page"

patterns-established:
  - "Two-tier card: summary default view with expand/collapse for detailed steps and code snippets"
  - "Optimistic update with rollback: update local state immediately, revert on API error"
  - "Tab navigation with filter row: tabs control view mode, filters control content within view"

requirements-completed: [REC-01, REC-02, REC-03, REC-04, REC-05]

# Metrics
duration: 4min
completed: 2026-02-23
---

# Phase 8 Plan 03: Recommendations Frontend Summary

**Two-tier recommendation cards with expand/collapse, progress tracking, per-engine sentiment breakdown, content gap topic cards, and Markdown fix plan export on a tabbed recommendations page**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-22T23:10:10Z
- **Completed:** 2026-02-22T23:14:11Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- 4 reusable Vue components: RecommendationCard (two-tier), RecommendationProgress (animated bar), SentimentBreakdown (per-engine grid), ContentGapCard (topic with brief)
- Full /recommendations page with 4 tabs (By Priority, By Page, Content Gaps, Sentiment), category/status filters, and Markdown export
- Audit page enhanced with recommendation preview section (progress bar + top 5 high-priority items)
- Sidebar navigation updated with Recommendations item accessible from all dashboard pages

## Task Commits

Each task was committed atomically:

1. **Task 1: Create RecommendationCard, RecommendationProgress, SentimentBreakdown, ContentGapCard components** - `089fe916` (feat)
2. **Task 2: Create recommendations page, update sidebar nav, add audit preview** - `dac57380` (feat)

## Files Created/Modified
- `frontend/components/RecommendationCard.vue` - Two-tier card with expand/collapse, priority badges, done/dismiss/undo buttons, code snippet display
- `frontend/components/RecommendationProgress.vue` - Animated progress bar with per-priority remaining counts
- `frontend/components/SentimentBreakdown.vue` - Per-engine sentiment grid with mini bars and dominant labels
- `frontend/components/ContentGapCard.vue` - Topic card with expandable mini brief section
- `frontend/pages/recommendations.vue` - Full page with tabs, filters, parallel API loading, optimistic status updates, Markdown export
- `frontend/pages/audit.vue` - Added recommendation preview section with progress bar and top 5 high-priority items
- `frontend/layouts/dashboard.vue` - Replaced Optimization with Recommendations nav item

## Decisions Made
- Replaced the existing "Optimization" nav item with "Recommendations" using the same LightBulbIcon, since the recommendations page supersedes the old optimization placeholder
- Implemented optimistic status updates: local state updates immediately on done/dismiss clicks, rolling back if the PATCH request fails
- Sentiment and content gap API calls wrapped with .catch(() => null) for fail-silent loading (supplementary data should not block the main recommendation list)
- Page groups in the "By Page" tab auto-expand on initial load so users see all content immediately
- Recommendation preview on audit page limited to top 5 high-priority open items to keep the audit page scannable

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required. All components consume existing Phase 8 API endpoints.

## Next Phase Readiness
- Phase 8 (Actionable Recommendations) is now complete with backend engine, API layer, and frontend experience
- Recommendation data flows end-to-end: audit pipeline generates recommendations, API serves them, frontend displays and manages them
- Ready for Phase 9 (Dashboard & Reporting) which can consume recommendation progress data for dashboard widgets

## Self-Check: PASSED

All 7 created/modified files verified present. Both commit hashes (089fe916, dac57380) verified in git log.

---
*Phase: 08-actionable-recommendations*
*Completed: 2026-02-23*
