# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-21)

**Core value:** Show brands exactly how AI engines see them -- with real quotes from real AI responses, not just theoretical scores.
**Current focus:** Phase 6 COMPLETE. Ready for Phase 7: Auto-Competitor Discovery

## Current Position

Phase: 6 of 9 (Site AI-Readiness Scoring) -- COMPLETE
Plan: 5 of 5 in current phase (5 complete)
Status: Completed 06-05 (AuthorityScorer + Optimization Score UI) -- Phase 6 done
Last activity: 2026-02-22 -- Completed 06-05 (AuthorityScorer + Optimization Score UI)

Progress: [################] 67%

## Performance Metrics

**Velocity:**
- Total plans completed: 16
- Average duration: 4 min
- Total execution time: 1.2 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-foundation-safety | 3 | 11 min | 4 min |
| 02-site-crawl-query-generation | 2 | 8 min | 4 min |
| 03-ai-engine-dispatch | 2 | 5 min | 3 min |
| 04-mention-detection-scoring | 2 | 6 min | 3 min |
| 05-audit-experience | 2 | 6 min | 3 min |
| 06-site-ai-readiness-scoring | 5 | 32 min | 6 min |

**Recent Trend:**
- Last 5 plans: 05-02 (3min), 06-01 (5min), 06-02 (4min), 06-03 (5min), 06-05 (49min)
- Trend: 06-05 larger due to full-stack (23-criteria scorer + API + frontend)

*Updated after each plan completion*
| Phase 02 P01 | 4min | 2 tasks | 9 files |
| Phase 02 P02 | 4min | 2 tasks | 5 files |
| Phase 03 P01 | 3min | 2 tasks | 7 files |
| Phase 03 P02 | 2min | 2 tasks | 3 files |
| Phase 04 P01 | 4min | 3 tasks | 9 files |
| Phase 04 P02 | 2min | 2 tasks | 3 files |
| Phase 05 P01 | 3min | 2 tasks | 7 files |
| Phase 05 P02 | 3min | 3 tasks | 6 files |
| Phase 06 P01 | 5min | 2 tasks | 14 files |
| Phase 06 P05 | 49min | 2 tasks | 14 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: Auth and cost controls must be in place before any AI API code (safety-first ordering)
- [Roadmap]: Pipeline built in vertical layers (crawl -> generate -> dispatch -> analyze -> score) not horizontal layers
- [Roadmap]: Competitive intelligence and brand analysis depend on core audit, not on each other (phases 6 and 7 can run after phase 5)
- [01-01]: Used explicit BcryptHasher instead of PasswordHash.recommended() to avoid argon2 dependency
- [01-01]: Created Alembic migration manually since no local DB for autogenerate
- [01-01]: Made SUPABASE_URL/KEY optional for self-managed auth transition
- [01-02]: Created migration 002 manually (no local DB for autogenerate)
- [01-02]: audit_id is plain UUID (no FK) -- audits table comes in Phase 2
- [01-02]: Celery module path matches docker-compose: celery -A app.tasks.celery_app
- [01-03]: Cache service fails open (Redis outage does not block AI calls)
- [01-03]: Outbound rate limiter fails closed (back-pressure via blocking)
- [01-03]: Rate limiter is in-process (asyncio), not Redis-backed -- sufficient for single-worker Phase 1
- [01-03]: Stripe webhook left without JWT auth (secured by webhook signature)
- [02-01]: CrawlerService uses httpx async for page fetch, httpx sync for robots.txt
- [02-01]: robots.txt AI bot check returns tri-state: True (allowed), False (blocked), None (no directive)
- [02-01]: Migration 003 FK from audit_cost_ledger uses try/except for orphan row safety
- [02-01]: Content extraction cascade: main > article > largest div > body (follows existing pattern)
- [02-02]: QueryGeneratorService.generate() is synchronous (litellm.completion is sync) -- safe in Celery
- [02-02]: Brand name extraction priority: schema.org Organization > og:site_name > title tag > domain
- [02-02]: Audit status set to COMPLETED after query gen (Phase 3 extends to DISPATCHING)
- [02-02]: GeneratedQuery category uses Literal type for compile-time and runtime validation
- [03-01]: Thread-local DB sessions in ThreadPoolExecutor (SQLAlchemy sessions are not thread-safe)
- [03-01]: Thread-local asyncio event loops for async cache and rate limiter calls from sync threads
- [03-01]: API key validation before engine call -- skip with error message if missing, not crash
- [03-01]: Perplexity surcharge added post-call since LiteLLM does not track Perplexity search fees
- [03-02]: DispatchSummary computed server-side from engine_responses (not stored in DB)
- [03-02]: model_validate + manual dispatch_summary assignment for response construction
- [04-01]: Deduplication by exact offset match, not 50-char window -- prevents collapsing legitimate separate mentions
- [04-01]: Short brand names (<4 chars) use case-sensitive matching to avoid false positives
- [04-01]: Fuzzy pass requires both token_set_ratio AND partial_ratio above threshold for dual validation
- [04-02]: QueryGeneratorService instantiated in Stage 4 for brand name re-extraction (instance method, not static)
- [04-02]: Backref visibility_score handled as list with isinstance check for forward-compatible access
- [04-02]: ANALYZING status added to dispatch_summary computation filter
- [05-01]: Removed @nuxtjs/supabase entirely -- self-managed JWT auth via useCookie
- [05-01]: useCookie('access_token') for token persistence (SSR-safe, persistent across reloads)
- [05-01]: useState for user state (shared across components, survives unmount)
- [05-01]: Login success redirects to /audit (primary Phase 5 feature page)
- [05-02]: useIntervalFn called at top level of script setup for proper Vue lifecycle cleanup
- [05-02]: HighlightMentions uses offset-based slicing only -- no string re-matching for fuzzy match accuracy
- [05-02]: Overlapping mentions handled by skipping mentions whose char_offset falls before cursor
- [05-02]: Polling interval 3 seconds with immediate:false to prevent polling on mount
- [06-01]: Weakest-link aggregation: 0.6 * mean + 0.4 * min across pages penalizes inconsistency
- [06-01]: Conditional scorer imports (try/except ImportError) allow pipeline to work with 0-4 scorers
- [06-01]: ScoringCriterionResult dataclass separate from CriterionResult SQLAlchemy model
- [06-01]: SKIP_URL_PATTERNS excludes login, admin, assets, static files from link discovery
- [06-05]: External APIs (Knowledge Graph, Wikidata, Wikipedia, PageSpeed) degrade gracefully -- _not_checked on failure, not score=0
- [06-05]: Backlink criteria (S9, S10) use proxy signals (internal links, sameAs, outbound authority links) instead of paid APIs
- [06-05]: PageSpeed API only called for homepage, cached per domain -- avoids rate limits on 25-page crawls
- [06-05]: CWV and sitemap results cached per domain to avoid redundant API calls across pages

### Pending Todos

None yet.

### Blockers/Concerns

- [Research]: Verify current AI provider API pricing before Phase 1 cost modeling
- [Research]: Verify Perplexity API model names (sonar) are still current
- [Research]: Review provider TOS for output storage before Phase 1 schema design
- [Codebase]: Six existing concerns from CONCERNS.md must be resolved in Phase 1 (disabled auth, .env committed, rate limiter fails open, BackgroundTasks instead of Celery, random number fallbacks, dual ORM)

## Session Continuity

Last session: 2026-02-22
Stopped at: Completed 06-05-PLAN.md (AuthorityScorer + Optimization Score UI) -- Phase 6 COMPLETE
Resume file: .planning/phases/06-site-ai-readiness-scoring/06-05-SUMMARY.md
