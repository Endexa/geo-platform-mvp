# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-26)

**Core value:** A user enters a URL, gets a real, trustworthy score with actionable recommendations they can immediately act on.
**Current focus:** Phase 8: Code Analysis

## Current Position

Phase: 8 of 8 (Code Analysis) -- Complete
Plan: 2 of 2 complete
Status: Phase 8 complete (backend + frontend + tests)
Last activity: 2026-02-26 -- 08-02 executed (useCodeAnalysis composable, CodeAnalysisPrompts, CodeAnalysisUpload, CodeRecommendationCard, audit.vue integration, 25 unit tests)

Progress: [██████████] 100% (8/8 phases complete)

## Performance Metrics

**Velocity:**
- Total plans completed: 17
- Average duration: 4.4min
- Total execution time: 1.23 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-scoring-foundation | 2/2 | 5min | 2.5min |
| 02-recommendations-competitor-benchmarking | 3/3 | 14min | 4.7min |
| 03-ai-visibility-hardening | 2/2 | 9min | 4.5min |
| 04-payments-freemium-gating | 2/2 | 10min | 5min |
| 05-reports-exports | 2/2 | 9min | 4.5min |
| 06-chat-assistant | 2/2 | 10min | 5min |
| 07-dashboard-frontend-polish | 3/3 | 18min | 6min |

**Recent Trend:**
- Last 5 plans: 06-02 (5min), 07-01 (7min), 07-02 (3min), 07-03 (8min)
- Trend: Consistent (fast execution)

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
- [02-02]: Brand linking uses 4-level priority: domain match > exact name > fuzzy name (>90 token_set_ratio) > create new
- [02-02]: SOV trend joins DiscoveredCompetitor with Audit to get audit dates, ordered ascending
- [02-02]: Score comparison reads site category scores from PageScore averages, not a JSONB field
- [02-02]: Migration numbered 011 to chain after existing 010 from plan 02-01
- [03-01]: Weighted-by-queries-sent scoring replaces equal-weight averaging for overall visibility score
- [03-01]: Confidence thresholds: 0=not_measured, 1-4=low, 5-9=medium, 10+=high (no external deps)
- [03-01]: Enriched JSONB coexistence: old {"openai": 75} and new {"openai": {...}} formats in same column
- [04-01]: StripeClient instance pattern (not deprecated stripe.api_key global) -- SDK v14+
- [04-01]: construct_event for webhook verification (returns full Event with data.object)
- [04-01]: Upsert pattern in webhook handlers for out-of-order event tolerance
- [04-01]: WebhookEvent table for idempotent deduplication (not Redis)
- [04-02]: require_tier() FastAPI dependency factory for server-side feature gating
- [04-02]: Audit filtering at read time only (pipeline runs all scorers regardless of tier)
- [04-02]: Free tier shows crawlability + overall score + top 3 recs (enough for "aha moment")
- [04-02]: Session-status polling on success page handles webhook race (5 attempts, 2s apart)
- [05-01]: ReportService uses Jinja2+WeasyPrint for HTML/PDF; CSV with BOM for Excel compatibility
- [05-01]: Combined GEO score = round(visibility * 0.15 + optimization * 0.85)
- [05-01]: Template resolves via os.path.dirname relative path (not hardcoded)
- [05-01]: CSV priority mapping: high->Highest, medium->Medium, low->Low (Jira standard)
- [05-02]: 29 unit tests cover executive summary, CSV export, HTML/PDF rendering, tier gating
- [06-01]: API key resolved via prefix matching (gemini/ -> GEMINI_API_KEY) -- same pattern as dispatch_service.py
- [06-01]: User message saved to DB before LLM call to persist even if streaming fails
- [06-01]: JSONB messages array on ChatSession (not separate ChatMessage table) -- conversation always loaded/saved as whole
- [06-01]: System prompt limited to top 15 failing criteria + top 10 recommendations to avoid context overflow
- [06-02]: fetchEventSource over native EventSource for POST + auth headers on SSE chat endpoint
- [06-02]: ChatPanel uses Teleport to body to avoid z-index stacking context issues
- [06-02]: Plain text with whitespace-pre-wrap for assistant messages (markdown rendering deferred to future)
- [07-02]: useBrandSelector uses Nuxt useState (not Pinia) for SSR-safe brand state that persists across navigations
- [07-02]: CategoryBreakdown receives data from latest audit history entry rather than a separate API call
- [07-02]: Brand selector hidden for single-brand users (brands.length <= 1)
- [07-02]: TrendChart tension reduced to 0.1 to avoid implying interpolation between sparse audit snapshots
- [Phase 07-01]: Chart.js colors centralized in chartColors.ts utility using rgb() format instead of hex
- [Phase 07-01]: Sidebar uses two states only (full open / fully hidden) -- no icon-only collapsed mode
- [Phase 07-01]: Upgrade CTA conditionally hidden for pro users via useSubscription composable
- [08-01]: Prompt generation is template-based with zero LLM calls -- sub-200ms guaranteed, no per-call cost
- [08-01]: IP protection enforced -- CATEGORY_TEMPLATES contain only diagnostic questions, zero criterion IDs/scores/weights
- [08-01]: Download endpoint is /prompts/download (separate route) rather than Accept-header switching -- avoids FastAPI response_model conflict
- [08-01]: LiteLLM parse_output uses response_format=CodeAnalysisResult with explicit api_key= (same pattern as chat_service.py)
- [08-02]: CodeRecommendationCard extracted as standalone component -- keeps CodeAnalysisUpload template manageable (single-responsibility)
- [08-02]: Celery task unit tests use task.run() (not __wrapped__) to bypass Celery dispatch while respecting bind=True signature
- [08-02]: IP protection test uses three regex patterns + forbidden words + score fractions -- comprehensive CODE-04 coverage

### Pending Todos

None yet.

### Blockers/Concerns

- ~~103/108 legacy data points return hardcoded zeros -- Phase 1 must replace all of them~~ RESOLVED: deleted in 01-01
- ~~Legacy `geo_data_points/` directory is dead code that must be deleted (Phase 1)~~ RESOLVED: deleted in 01-01
- Gemini free tier instability -- Google has slashed limits; may need paid tier for production
- LiteLLM pinning risk -- current version is 2 years old, upgrade needed but LiteLLM breaks between minors
- Stripe setup requires manual configuration: product creation in Stripe Dashboard, env vars for price IDs
- Integration tests requiring Supabase DB are skipped in local dev (only unit tests run locally)

## Session Continuity

Last session: 2026-02-26
Stopped at: Completed 08-02-PLAN.md (code analysis frontend + tests -- Phase 8 complete)
Resume file: None
