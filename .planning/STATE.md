# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-21)

**Core value:** Show brands exactly how AI engines see them -- with real quotes from real AI responses, not just theoretical scores.
**Current focus:** Phase 3: AI Engine Dispatch

## Current Position

Phase: 3 of 9 (AI Engine Dispatch)
Plan: 1 of 2 in current phase
Status: In Progress
Last activity: 2026-02-22 -- Completed 03-01 (EngineResponse model, DispatchService)

Progress: [######░░░░] 30%

## Performance Metrics

**Velocity:**
- Total plans completed: 6
- Average duration: 4 min
- Total execution time: 0.35 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-foundation-safety | 3 | 11 min | 4 min |
| 02-site-crawl-query-generation | 2 | 8 min | 4 min |
| 03-ai-engine-dispatch | 1 | 3 min | 3 min |

**Recent Trend:**
- Last 5 plans: 01-02 (2min), 01-03 (5min), 02-01 (4min), 02-02 (4min), 03-01 (3min)
- Trend: stable

*Updated after each plan completion*
| Phase 02 P01 | 4min | 2 tasks | 9 files |
| Phase 02 P02 | 4min | 2 tasks | 5 files |
| Phase 03 P01 | 3min | 2 tasks | 7 files |

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

### Pending Todos

None yet.

### Blockers/Concerns

- [Research]: Verify current AI provider API pricing before Phase 1 cost modeling
- [Research]: Verify Perplexity API model names (sonar) are still current
- [Research]: Review provider TOS for output storage before Phase 1 schema design
- [Codebase]: Six existing concerns from CONCERNS.md must be resolved in Phase 1 (disabled auth, .env committed, rate limiter fails open, BackgroundTasks instead of Celery, random number fallbacks, dual ORM)

## Session Continuity

Last session: 2026-02-22
Stopped at: Completed 03-01-PLAN.md (EngineResponse model, DispatchService)
Resume file: .planning/phases/03-ai-engine-dispatch/03-01-SUMMARY.md
