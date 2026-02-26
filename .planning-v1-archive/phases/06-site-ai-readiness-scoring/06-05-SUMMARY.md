---
phase: 06-site-ai-readiness-scoring
plan: 05
subsystem: scoring, api, ui
tags: [authority, eeat, seo, pagespeed, knowledge-graph, wikidata, wikipedia, scoring, optimization-score, vue, tailwind]

# Dependency graph
requires:
  - phase: 06-02
    provides: CrawlabilityScorer (12 criteria)
  - phase: 06-03
    provides: ContentStructureScorer (13 criteria)
  - phase: 06-04
    provides: StructuredDataScorer (13 criteria)
provides:
  - AuthorityScorer with 23 criteria (8 E-E-A-T + 15 SEO fundamentals)
  - Optimization Score in audit API response with per-category averages
  - Frontend dual-score display (Visibility + Optimization)
  - CategoryBreakdown with click-to-drill-down
  - CriterionDrilldown with per-page per-criterion pass/fail and expandable details
  - Complete Phase 6 scoring experience (61 criteria, 4 categories)
affects: [07-auto-competitor, 08-recommendations, 09-dashboard, 10-scale]

# Tech tracking
tech-stack:
  added: [httpx (async API calls), bs4 (HTML parsing for authority checks)]
  patterns: [graceful-api-degradation, proxy-signals-for-paid-apis, cwv-caching-per-domain, dual-score-architecture]

key-files:
  created:
    - backend/app/services/scoring/authority_scorer.py
    - frontend/components/OptimizationScore.vue
    - frontend/components/CategoryBreakdown.vue
    - frontend/components/CriterionDrilldown.vue
  modified:
    - backend/app/services/scoring/__init__.py
    - backend/app/api/audit.py
    - backend/app/schemas/audit.py
    - frontend/pages/audit.vue
    - frontend/components/AuditResults.vue
    - frontend/components/AuditProgress.vue
    - CLAUDE.md
    - docs/progression.md

key-decisions:
  - "External APIs (Knowledge Graph, Wikidata, Wikipedia, PageSpeed) degrade gracefully -- _not_checked on failure, not score=0"
  - "Backlink criteria (S9, S10) use proxy signals (internal links, sameAs, outbound authority links) instead of paid APIs"
  - "PageSpeed API only called for homepage, cached per domain -- avoids rate limits on 25-page crawls"
  - "CWV and sitemap results cached per domain to avoid redundant API calls across pages"

patterns-established:
  - "Graceful API degradation: all external API calls return _not_checked on failure, excluded from scoring average"
  - "Proxy signals for paid APIs: internal link count + sameAs + outbound authority links substitute for Ahrefs/Moz DR/DA"
  - "Per-domain caching: PageSpeed and sitemap checks cached after first page, reused for all pages on same domain"
  - "Dual-score UI: Visibility Score + Optimization Score displayed side by side with category breakdown drill-down"

requirements-completed: [READY-04, READY-05, READY-06]

# Metrics
duration: 49min
completed: 2026-02-22
---

# Phase 6 Plan 05: AuthorityScorer + Optimization Score UI Summary

**AuthorityScorer with 23 criteria (8 E-E-A-T + 15 SEO fundamentals), external API integration (Knowledge Graph, Wikidata, Wikipedia, PageSpeed), audit API wired with OptimizationScore, and frontend dual-score display with per-category drill-down completing all 61 Phase 6 criteria**

## Performance

- **Duration:** 49 min
- **Started:** 2026-02-22T17:21:50Z
- **Completed:** 2026-02-22T18:10:55Z
- **Tasks:** 2
- **Files modified:** 14

## Accomplishments

- AuthorityScorer implements 23 criteria: A1-A8 E-E-A-T (author bios, dates, Knowledge Graph, Wikidata, Wikipedia, review profiles, brand signal, composite) + S1-S15 SEO fundamentals (SSL, canonical, meta title/desc, sitemap, OG, mobile, internal links, backlink proxies, CWV, URL structure, alt text, broken links, orphan pages)
- All external APIs (Google Knowledge Graph, Wikidata, Wikipedia, PageSpeed Insights) called with graceful degradation -- API failures return _not_checked and are excluded from scoring
- Audit API returns OptimizationScoreSchema with per-category averages, page_scores with criterion_results, and transparent pages_scored/pages_discovered counts
- Frontend shows Visibility + Optimization scores side by side, CategoryBreakdown in 2x2 grid with click-to-drill-down, CriterionDrilldown with pass/fail icons, expandable technical details, and evidence
- SCORING step added to AuditProgress stepper; discovered-but-not-scored pages shown at bottom of results
- Phase 6 complete: 61 criteria across 4 categories (Crawlability 12, Content Structure 13, Structured Data 13, Authority 23) with research-backed weights

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement AuthorityScorer with 23 criteria and export from scoring package** - `d83d380d` (feat)
2. **Task 2: Expose Optimization Score in audit API and build frontend scoring display** - `9946f6a3` (feat)

## Files Created/Modified

- `backend/app/services/scoring/authority_scorer.py` - AuthorityScorer with 23 criteria (1853 lines), asyncio semaphore for API rate limiting, per-domain CWV/sitemap caching
- `backend/app/services/scoring/__init__.py` - Added AuthorityScorer to package exports
- `backend/app/api/audit.py` - Eager-load page_scores with criterion_results, compute per-category averages, build OptimizationScoreSchema
- `backend/app/schemas/audit.py` - PageScoreSchema, CriterionResultSchema, OptimizationScoreSchema (already existed from 06-01, verified complete)
- `frontend/components/OptimizationScore.vue` - Dual-score hero cards (Visibility + Optimization) with color coding and pages summary bar
- `frontend/components/CategoryBreakdown.vue` - 2x2 grid of category cards with score bars, weights, and status labels
- `frontend/components/CriterionDrilldown.vue` - Per-page criterion list with pass/fail/not-checked icons, expandable technical details and evidence
- `frontend/components/AuditResults.vue` - Wired OptimizationScore, CategoryBreakdown, CriterionDrilldown, and unscored pages section
- `frontend/components/AuditProgress.vue` - Added SCORING step (step 5) between ANALYZING and COMPLETED
- `frontend/pages/audit.vue` - Types updated with optimization_score and page_scores fields
- `CLAUDE.md` - Updated Scoring System section with dual-score architecture, Current State table with Phase 6
- `docs/progression.md` - Added Phase 6 Plan 05 completion entry

## Decisions Made

- **Graceful API degradation:** All external API calls (Knowledge Graph, Wikidata, Wikipedia, PageSpeed) return `_not_checked` on failure with descriptive reason. Criteria marked `checked=False` are excluded from the category average, so API failures do not penalize the score.
- **Backlink proxy signals:** S9 (backlink profile) and S10 (referring domains) use composite proxy signals (internal link count, sameAs links from Organization schema, outbound authority links to .edu/.gov/wikipedia) instead of requiring paid Ahrefs/Moz APIs. Technical detail explicitly notes the proxy nature.
- **PageSpeed homepage-only:** CWV check (S11) only calls PageSpeed API for the first page on a domain, caching the result. This avoids rate limiting when scoring 25 pages. Similarly, sitemap check (S5) is cached per domain.
- **E-E-A-T composite:** A8 computes a weighted average of A1-A7 checked results only, providing a single E-E-A-T signal even when some API checks fail.

## Deviations from Plan

None - plan executed exactly as written. All files, criteria, API endpoints, and frontend components match the plan specification.

## Issues Encountered

None - both tasks completed cleanly. Frontend build passes with no TypeScript errors.

## User Setup Required

None - no external service configuration required. Google API key (GOOGLE_API_KEY) is optional; Knowledge Graph, PageSpeed, and Wikidata checks gracefully degrade without it.

## Next Phase Readiness

- Phase 6 is complete: all 61 criteria across 4 categories are operational
- The scoring pipeline feeds directly into Phase 8 (Recommendations) which can use criterion results to generate specific, actionable advice
- Phase 7 (Auto-Competitor) can extract competitor brands from AI responses and score them using the same pipeline
- Phase 9 (Dashboard) can display historical optimization scores over time

## Self-Check: PASSED

- All 5 key files exist on disk
- Both task commits (d83d380d, 9946f6a3) found in git log
- Frontend build passes with no errors

---
*Phase: 06-site-ai-readiness-scoring*
*Completed: 2026-02-22*
