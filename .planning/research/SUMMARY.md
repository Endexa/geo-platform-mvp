# Project Research Summary

**Project:** Endexa GEO Platform v2
**Domain:** GEO/SEO SaaS Audit Platform
**Researched:** 2026-02-25
**Confidence:** HIGH

## Executive Summary

Endexa v2 is a rebuild of a GEO/SEO audit platform that has working infrastructure (FastAPI + Celery + Supabase + 4 AI engines) but broken scoring (103/108 data points return zeros, recommendations are stubs, visibility scores use mock data). The market is exploding -- Profound just raised $96M at a $1B valuation, and every SEO tool from Semrush to Ahrefs is bolting on GEO. But a glaring gap exists: no tool under $50/month combines SEO and GEO auditing with actionable, prioritized recommendations. Competitors either monitor without advising (Otterly, Geneo), advise on content without technical depth (Frase), or charge $200-800+/month for real value (Profound, Semrush, Ahrefs). Endexa's structural advantage is a 53-criteria scoring system spanning both SEO and GEO, auto-competitor discovery from AI responses, code-level analysis (unique in the entire market), and Jira export for developer teams.

The recommended approach is to treat the scoring pipeline as the absolute first priority. Every feature -- recommendations, reports, chat, dashboard, payments -- depends on scores being real. The existing 61-criteria framework is architecturally sound but produces zeros. Phase 1 must make every criterion produce real measurements with a three-state system (PASS/FAIL/NOT_MEASURED), then wire recommendations to use real data. Only after scoring and recommendations work should the team build output features (reports, exports, payments) and interactive features (chat, code analysis). The existing stack needs minimal additions: 1 new backend package (sse-starlette), 5 new frontend packages (marked, highlight.js, DOMPurify, @stripe/stripe-js, marked-highlight), and 3 upgrades (Stripe, LiteLLM, WeasyPrint).

The key risks are: (1) shipping fabricated scores that SEO professionals will immediately detect and publicly expose, destroying credibility; (2) AI visibility measurement non-determinism where scores swing 20+ points between identical audits; and (3) LLM API cost spirals where free-tier abuse or viral moments generate $5K+ bills overnight. All three are preventable with specific engineering practices: three-state scoring, statistical multi-query measurement, and hard per-user spending caps. The competitive window is open now but closing fast -- Semrush, Ahrefs, and Geoptie are all pushing into the SEO+GEO space.

## Key Findings

### Recommended Stack

The existing FastAPI + Nuxt 3 + Supabase + Celery + Redis stack is solid and needs no replacement. The rebuild is about adding capabilities to this foundation, not changing it. Total new dependencies are remarkably small: 1 new Python package and 5 new npm packages.

**Core additions and upgrades:**
- **sse-starlette** (new): Server-Sent Events for chat assistant LLM streaming -- SSE is the standard pattern used by OpenAI and Anthropic, simpler than WebSockets for unidirectional streaming
- **Stripe SDK 7.9 -> 14.x** (upgrade): The old `stripe.api_key` global pattern is deprecated; v14 uses instance-based `StripeClient` which aligns with the project's existing explicit api_key passing pattern
- **LiteLLM 1.17 -> 1.81** (upgrade): Current version is 2 years old; v1.75+ adds MCP support, 50% memory leak reduction, better streaming -- pin exact version as LiteLLM breaks between minors
- **marked + highlight.js + DOMPurify** (new frontend): Markdown rendering for chat responses with XSS sanitization -- DOMPurify is security-critical since LLM output is rendered as HTML
- **@stripe/stripe-js** (new frontend): Checkout Session redirect -- start with redirect flow, not inline Payment Elements

**Key removal:** langchain + langchain-openai + openai (200MB+ of unused dependencies). All LLM calls go through LiteLLM.

**Architecture decisions baked into stack:**
- Chat uses prompt stuffing, NOT RAG (audit data is 5-15KB, fits easily in 128K context)
- PDF reports use WeasyPrint + Jinja2 (already installed), with CSS-styled HTML charts, not Chart.js
- CSV/Jira export uses Python stdlib csv module (not pandas)
- Recommendations engine is deterministic (rule-based gap analysis), NOT LLM-powered

### Expected Features

**Must have (table stakes -- v2.0 launch):**
- [TS-1] Working URL-based audit producing real scores across all 61 criteria -- the critical path root
- [TS-2] Multi-engine AI visibility tracking across 4 engines with per-engine breakdown
- [TS-3] Overall GEO readiness score (0-100) with dual Visibility + Optimization architecture
- [TS-4] Category breakdown scores across 4 weighted categories
- [TS-6] Actionable, prioritized recommendations with evidence and code snippets -- the #1 conversion driver
- [TS-9] Freemium entry point: free crawlability audit, paid unlocks full audit + recommendations
- [TS-10] Authentication + saved audit history (already built)

**Should have (differentiators -- v2.x):**
- [D-1] SEO + GEO combined audit -- nearly uncontested in the market; only Frase does dual scoring but content-only
- [TS-5] Competitor comparison with auto-discovery from AI responses
- [D-5] Priority-ordered recommendations with calculated impact estimates ("Fix this = +X points")
- [TS-7] PDF/HTML audit report export for agencies
- [D-3] Jira/CSV export with structured stories -- unique in the market
- [TS-8] Dashboard with score history and trend tracking
- [D-7] Per-page drill-down with weakest-link aggregation

**Defer (v3+):**
- [D-6] Chat assistant for audit Q&A
- [D-2] Code analysis flow (novel but unvalidated)
- [D-8] Multi-site management for agencies
- White-label reports, CRM integrations, Brand Signature Engine
- Real-time continuous monitoring (too expensive in API costs)
- AI content generation (different product category, not our lane)

### Architecture Approach

The architecture centers on the Audit as the aggregate root, with all features radiating from it. The existing 19-table data model needs 5 new tables (chat_sessions, audit_reports, subscriptions, code_analysis_prompts, code_analysis_results). The build order is strictly dependency-driven: Scoring Pipeline first (everything depends on real scores), then Recommendations + Competitor Benchmarking (immediate value from real data), then output features (reports, exports, payments), then interactive features (chat, code analysis), and finally the production dashboard.

**Major components:**
1. **ScoringPipeline** -- Run 61 criteria against crawled pages, produce real measurements (CRITICAL PATH)
2. **RecommendationEngine** -- Deterministic gap analysis comparing scores against benchmarks and competitor averages
3. **CompetitorBenchmarking** -- NER-based competitor discovery, parallel crawl+score, leaderboard with share-of-voice
4. **PaymentGating** -- Stripe Checkout Sessions, webhook handling, tier-based feature gating via FastAPI dependencies
5. **ReportGenerator** -- Jinja2 HTML templates rendered to PDF via WeasyPrint in Celery workers
6. **JiraCSVExport** -- Server-side CSV generation with configurable Jira column mapping
7. **ChatAssistant** -- SSE-streamed LLM responses with audit data as context (prompt stuffing)
8. **CodeAnalysisFlow** -- Generate prompts for users to run on their repos, ingest output for deeper analysis
9. **ProductionDashboard** -- Real metrics from all components, trend charts, audit history

**Key patterns to follow:** Celery tasks for operations >2s, FastAPI Depends() for tier gating, audit ownership verification on every endpoint, context-aware LLM prompts for chat.

**Key anti-patterns to avoid:** LLM for deterministic logic (recommendations must be rule-based), synchronous heavy operations in API handlers, fat monolithic Celery tasks, N+1 queries.

### Critical Pitfalls

1. **Fabricated scores (CREDIBILITY KILLER)** -- The v1 gave a site with zero AI mentions a 69/100 visibility score. SEO professionals will verify and publicly expose this. Prevention: implement three-state system (PASS/FAIL/NOT_MEASURED), exclude unmeasured criteria from aggregation, validate against 10 known sites before launch.

2. **AI visibility non-determinism** -- AirOps research found only 30% of brands stayed visible across consecutive LLM queries. A single-query check is meaningless. Prevention: run 5-15 queries per engine, report mention rates with confidence intervals, use temperature=0, cache with 7-day TTL, track trends instead of absolutes.

3. **LLM API cost spiral** -- Each audit = 40 LLM calls at $0.10-0.15. Free-tier abuse can multiply costs 10x overnight. Prevention: enforce per-audit budget caps, use cheap models (Gemini Flash, GPT-4o-mini) for most queries, cache aggressively (7-day TTL), rate-limit free tier (3 audits/day, no AI queries), set hard monthly spending caps per tier.

4. **Irrelevant recommendations** -- The v1 recommended ClaimReview schema for a student SaaS and VideoObject for a site with no videos. All recommendations showed identical "+5%" impact. Prevention: require vertical classification, generate recommendations from actual measurement data (not static checklist), include copy-paste-ready fixes, calculate impact from measurement deltas, filter by site type.

5. **Rebuilding on half-working code** -- Two parallel systems exist (old 108-point geo_data_points/ vs new 61-criteria scoring/). Hidden import chains and shared DB schemas create invisible coupling. Prevention: do NOT fix the old system, build everything in backend/app/services/scoring/, delete geo_data_points/ in Phase 1, add integration tests as safety net before refactoring.

## Implications for Roadmap

Based on combined research, the following 8-phase structure maps to dependencies, architecture boundaries, and pitfall avoidance.

### Phase 1: Scoring Foundation
**Rationale:** The critical path root. Every other feature -- recommendations, reports, chat, dashboard, payments -- depends on scores being real. Nothing ships until this works.
**Delivers:** All 61 criteria producing real measurements from crawl data. Three-state system (PASS/FAIL/NOT_MEASURED). Crawler enrichment for missing data signals. Integration test that runs a full audit against a known site and verifies output. Dead code cleanup (remove geo_data_points/).
**Addresses:** TS-1 (URL-based audit), TS-3 (overall score), TS-4 (category breakdown), D-1 (SEO+GEO combined)
**Avoids:** Pitfall 1 (fabricated scores), Pitfall 5 (integration debt), Pitfall 8 (SPA crawl failures)

### Phase 2: Recommendations + Competitor Benchmarking
**Rationale:** The #1 conversion driver (recommendations) and the most-requested context feature (competitor comparison) both depend on Phase 1 scores. The existing deterministic recommendation engine framework just needs real data to produce real output. Competitor benchmarking adds the "competitor_avg" data that recommendations use for gap analysis.
**Delivers:** Working recommendation engine with evidence, code snippets, action steps, and calculated impact estimates. Auto-competitor discovery via NER, URL resolution, parallel crawl+score. Leaderboard with share-of-voice. Vertical-aware recommendation filtering.
**Addresses:** TS-5 (competitor comparison), TS-6 (actionable recommendations), D-5 (impact estimates)
**Avoids:** Pitfall 4 (irrelevant recommendations), Pitfall 10 (scoring without calibration), Pitfall 11 (wrong competitors)

### Phase 3: AI Visibility Hardening
**Rationale:** The existing 4-engine dispatch works but treats visibility as a single-shot check. This phase makes it a statistical measurement system with confidence intervals, multi-query aggregation, and per-engine breakdowns. Must happen before public launch.
**Delivers:** Multi-query measurement (5-15 queries per engine), temperature=0 for measurement queries, mention rate reporting with confidence intervals, model routing (cheap models for bulk, expensive for final assessment), 7-day cache TTL for AI responses, per-engine breakdown dashboard.
**Addresses:** TS-2 (multi-engine visibility), polishes dual-score architecture
**Avoids:** Pitfall 2 (AI visibility non-determinism), Pitfall 3 (API cost spiral)

### Phase 4: Payments + Freemium Gating
**Rationale:** Must work before public launch. Independent of other features architecturally but blocks monetization. Stripe SDK upgrade is required.
**Delivers:** Working Stripe Checkout Session flow, webhook handling with idempotent handlers, subscription management, tier-based feature gating via FastAPI Depends(), reconciliation job for database/Stripe consistency, freemium gate (free crawlability, paid full audit).
**Addresses:** TS-9 (freemium entry point), enables monetization
**Avoids:** Pitfall 6 (freemium miscalibration), Pitfall 7 (Stripe webhook unreliability)
**Uses:** Stripe SDK 14.x, @stripe/stripe-js

### Phase 5: Reports + Exports
**Rationale:** High-perceived-value output features that convert free users to paid. Reports are essential for agencies. Jira export is a unique differentiator. Both consume completed audit data, so they are simple to build once Phases 1-2 are done.
**Delivers:** PDF/HTML audit report generation via Jinja2 + WeasyPrint (Celery task), Jira-compatible CSV export with configurable columns and grouping, download API endpoints gated by subscription tier.
**Addresses:** TS-7 (PDF/HTML export), D-3 (Jira export)
**Avoids:** Pitfall 12 (Jira export before recommendations are validated)

### Phase 6: Chat Assistant
**Rationale:** A differentiator (no competitor has audit Q&A chat), but requires working scores and recommendations as context. Lower priority than core audit features for launch.
**Delivers:** SSE-streamed LLM chat over audit results, prompt-stuffed context (not RAG), conversation persistence, DOMPurify-sanitized markdown rendering, budget-capped per audit.
**Addresses:** D-6 (chat assistant)
**Avoids:** Pitfall 9 (prompt leakage), Pitfall 3 (cost spiral from chat)
**Uses:** sse-starlette, marked, highlight.js, DOMPurify, LiteLLM streaming

### Phase 7: Dashboard + History
**Rationale:** Last major feature phase because it requires all other components producing real data. Building the dashboard over fake data is how v1 failed.
**Delivers:** Real metrics dashboard (not mock data), audit history with trend tracking, per-brand score progression, competitor positioning over time, recommendation progress tracking (done/open/dismissed), scoring version annotations on trend charts.
**Addresses:** TS-8 (dashboard with trends), D-7 (per-page drill-down)
**Avoids:** Pitfall 13 (stale/misleading trends)

### Phase 8: Code Analysis + Scale
**Rationale:** Novel but unvalidated feature (zero competitors offer it). Build only after core product is proven. Also includes scaling work needed as user base grows.
**Delivers:** Code analysis prompt generation from audit gaps, output ingestion + LLM parsing, enriched recommendations from code findings. Queue routing (separate Celery queues), connection pooling, pagination on all list endpoints.
**Addresses:** D-2 (code analysis flow), D-8 (multi-site management groundwork)
**Avoids:** Building unvalidated features before core is solid

### Phase Ordering Rationale

- **Phases 1-3 are the core audit loop.** Scoring -> Recommendations + Competitors -> AI Visibility Hardening. Each depends on the previous. Nothing else is worth building until this loop produces real, trustworthy results.
- **Phase 4 (Payments) is independent architecturally but blocks launch.** It can be built in parallel with Phase 3 by a separate developer.
- **Phases 5-6 are output/interaction layers** that consume audit data. They add value but do not change what the audit measures.
- **Phases 7-8 are polish and expansion.** Dashboard requires real data from all components. Code analysis is a bet on a novel feature.
- **The grouping follows architecture boundaries.** Each phase maps to 1-2 components from the architecture document, minimizing cross-cutting concerns per phase.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1 (Scoring Foundation):** Needs research per criterion category -- what exactly does each of the 61 criteria measure, what crawl data does it need, what are the thresholds? The ARCHITECTURE.md notes the crawler may need enrichment.
- **Phase 3 (AI Visibility Hardening):** Needs research on statistical measurement design -- how many queries per engine, what confidence interval is acceptable, how to handle engine-specific behaviors (Perplexity does live search, Claude rarely cites).
- **Phase 4 (Payments):** Needs research on Stripe Checkout Session v2 API changes from v7 to v14, webhook best practices, and test clock setup.
- **Phase 6 (Chat Assistant):** Needs research on SSE reconnection patterns, context window management for large audits, and prompt injection prevention.

Phases with standard patterns (skip research-phase):
- **Phase 2 (Recommendations):** The deterministic engine framework exists, gap analysis is well-documented, this is standard software engineering.
- **Phase 5 (Reports + Exports):** WeasyPrint + Jinja2 PDF generation and CSV export are thoroughly documented patterns.
- **Phase 7 (Dashboard):** Standard Chart.js + Vue composables + SQL aggregation queries. No novel patterns needed.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions verified via pip index/npm view. Minimal additions needed. Architecture decisions well-reasoned. |
| Features | HIGH | Based on competitor pricing pages, G2 reviews, and market research. 8 competitors analyzed with verified pricing. |
| Architecture | HIGH | Grounded in existing codebase audit. Component boundaries match real code. Data model evolution is incremental. |
| Pitfalls | HIGH | Grounded in actual v1 failures (fabricated scores, irrelevant recs, SPA crawl failures) plus industry research (OWASP, AirOps, Bessemer). |
| Competitors | HIGH | All 8 competitor pricing and features verified from official sources in Feb 2026. Market positioning is clear. |

**Overall confidence:** HIGH

### Gaps to Address

- **Scoring calibration dataset does not exist.** The 61 criteria use research-backed weights but have never been validated against actual AI citation rates. Need to build a 50-100 site calibration dataset during Phase 2 to validate that the optimization score correlates with AI visibility.
- **Freemium gate position is unvalidated.** The recommendation (free = crawlability only) is an educated guess. Need usage analytics from the first 50 free users to calibrate -- if conversion rate is below 2% after 60 days, the gate needs to move.
- **Gemini free tier instability.** Google slashed free tier limits by 50-92% in December 2025. Production deployment should budget for paid Gemini tier, not rely on free.
- **LiteLLM pinning risk.** LiteLLM releases multiple times per week with potential breaking changes. The recommendation to pin exact version (1.81.15) means manual upgrade management. Need a strategy for testing LiteLLM upgrades.
- **Code analysis feature demand is unvalidated.** Zero competitors offer this, which could mean "massive opportunity" or "nobody wants it." Defer to Phase 8 and validate demand before building.

## Sources

### Primary (HIGH confidence)
- Endexa codebase direct audit (19 existing tables, 61-criteria framework, working infrastructure)
- PyPI verified versions: stripe 14.3.0, litellm 1.81.15, weasyprint 68.1, sse-starlette 3.2.0
- npm verified versions: marked 17.0.3, highlight.js 11.11.1, DOMPurify 3.3.1, @stripe/stripe-js 8.8.0
- Profound pricing ($99-$399+/mo), Series C $96M at $1B valuation (SiliconAngle, Feb 24 2026)
- Otterly.AI pricing ($29-$489/mo), Geoptie pricing ($0-$199/mo), Frase.io pricing ($14.99-$114.99/mo)
- Semrush AI Visibility Toolkit ($99-$549/mo), Ahrefs Brand Radar ($328-$2,198/mo), BrightEdge ($12K-$150K+/yr)
- OWASP Top 10 for LLM Applications 2025 (prompt leakage, injection)
- Stripe webhook documentation (delivery ordering, 72-hour finalization)

### Secondary (MEDIUM confidence)
- AirOps LLM brand citation tracking (30% visibility consistency)
- Bessemer AI pricing playbook (50-60% AI SaaS margins)
- First Page Sage freemium conversion benchmarks (2-5% base, 8-15% top quartile)
- FastAPI + Celery production patterns (community guides)
- RAG vs prompt stuffing analysis (SpyglassMTG)
- WeasyPrint vs alternatives comparison (PDFBolt, Glukhov)
- Search Engine Land GEO audit guides

### Tertiary (needs validation)
- Gemini free tier stability (Google has changed limits multiple times; monitor continuously)
- Code analysis feature demand (zero market validation; build last)
- Optimal freemium gate position (requires real user data to calibrate)

---
*Research completed: 2026-02-25*
*Ready for roadmap: yes*
