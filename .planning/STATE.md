# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2025-02-25)

**Core value:** A user enters a URL, gets a real, trustworthy score with actionable recommendations they can immediately act on.
**Current focus:** Phase 2: Recommendations + Competitor Benchmarking

## Current Position

Phase: 2 of 8 (Recommendations + Competitor Benchmarking) -- IN PROGRESS
Plan: 1 of 3 in current phase
Status: 02-01-PLAN.md complete -- continuing Phase 2
Last activity: 2026-02-26 -- Completed 02-01-PLAN.md (vertical classifier + recommendation enhancements)

Progress: [██░░░░░░░░] 15%

## Performance Metrics

**Velocity:**
- Total plans completed: 3
- Average duration: 3.3min
- Total execution time: 0.17 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-scoring-foundation | 2/2 | 5min | 2.5min |
| 02-recommendations-competitor-benchmarking | 1/3 | 6min | 6min |

**Recent Trend:**
- Last 5 plans: 01-01 (2min), 01-02 (3min), 02-01 (6min)
- Trend: Consistent (fast execution)

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: Scoring pipeline is critical path root -- all other phases depend on real scores
- [Roadmap]: Recommendations and Competitor Benchmarking combined into single phase (tightly coupled via gap analysis)
- [Roadmap]: Dashboard and Frontend Polish combined into single phase (dashboard needs all real data; polish applies globally)
- [Roadmap]: Code Analysis is last phase (novel, unvalidated feature -- build after core product is proven)
- [01-01]: C9 SSR uses _not_checked on Playwright failure -- excluded from scoring instead of fabricated score=50
- [01-01]: Link discovery uses html field (full HTML) not main_content (stripped text) -- BeautifulSoup needs anchor tags
- [01-01]: Playwright cleanup wrapped in try/except in Celery task -- cleanup failure must not crash pipeline
- [01-01]: geo_datapoints.py router kept but imports disabled -- rewiring to new scoring is a future task
- [01-02]: stripe_crawl_data.json fixture exercises all 4 scorers with Organization + Article schemas, 5 sameAs links, FAQ section, author bio, 25+ internal links
- [01-02]: All scorer tests mock external HTTP calls -- no network dependencies, no API keys required
- [01-02]: Dual-score display (Visibility + Optimization) confirmed correct in AuditResults.vue and OptimizationScore.vue -- no changes needed
- [02-01]: Vertical exclusions use real criterion IDs (SD8=Product, SD10=ClaimReview) not research placeholder IDs
- [02-01]: Impact delta uses linear estimate with 15-point cap and 0.8 multi-page adjustment -- sufficiently accurate for user-facing estimates
- [02-01]: Content pattern matching can produce false positives but schema.org types take priority and resolve ambiguity

### Pending Todos

None yet.

### Blockers/Concerns

- ~~103/108 legacy data points return hardcoded zeros -- Phase 1 must replace all of them~~ RESOLVED: deleted in 01-01
- ~~Legacy `geo_data_points/` directory is dead code that must be deleted (Phase 1)~~ RESOLVED: deleted in 01-01
- Gemini free tier instability -- Google has slashed limits; may need paid tier for production
- LiteLLM pinning risk -- current version is 2 years old, upgrade needed but LiteLLM breaks between minors

## Session Continuity

Last session: 2026-02-26
Stopped at: Completed 02-01-PLAN.md
Resume file: None
