# Project Research Summary

**Project:** GEO Platform -- AI Brand Visibility Auditor
**Domain:** Generative Engine Optimization (GEO) / AI Brand Visibility Monitoring
**Researched:** 2026-02-21
**Confidence:** MEDIUM (architecture HIGH, stack HIGH, features MEDIUM, pitfall specifics MEDIUM)

## Executive Summary

The AI brand visibility auditing market is a nascent but fast-growing category (2024-2026) where commercial competitors (Profound, Otterly.ai, Peec AI, Knowatoa) have established table stakes expectations but left a clear gap: all require setup and onboarding, none offer a URL-first instant audit. The recommended approach builds directly on the existing FastAPI + Nuxt 3 + PostgreSQL + Celery + Redis stack, adding three new subsystems -- an AI engine query layer (using LiteLLM already installed at 1.80.7), an NLP brand mention analyzer (spaCy NER + rapidfuzz fuzzy matching), and a scoring pipeline with a transparent 0-100 GEO score. The core product is a 5-phase async pipeline: crawl site -> generate queries -> fan out to ChatGPT/Claude/Perplexity in parallel -> analyze brand mentions -> compute scores. The entire pipeline runs as a Celery task, returning `audit_id` immediately while the frontend polls for status.

The recommended architecture is well-founded in existing patterns and fits the codebase cleanly. The most important product decision confirmed by research is to stay tightly scoped to the one-time audit before building any monitoring: this avoids the classic trap of tracking unreliable data in an elaborate scheduling system before the core audit produces trustworthy results. The URL-first instant audit (no onboarding required) is the genuine differentiator the market is missing, enabled by the auto-query-generation feature that crawls the user's site and generates industry-relevant AI queries from the content.

The most critical risk is unit economics: each audit queries 3 engines with 10-15 prompts, costing approximately $0.03-0.08 per audit (with aggressive model tiering and caching), reaching $0.15-0.50 at the competitive-analysis tier. Cost controls -- per-audit budget caps, Redis response caching with 24h TTL, cheap model selection (gpt-4o-mini, claude-3-5-haiku), and Celery-based batching -- must be designed into the AI query layer from the start, not added later. Authentication must also be enabled before any AI audit endpoint is exposed, since a single unauthenticated endpoint can drain the entire API budget in minutes from automated requests.

## Key Findings

### Recommended Stack

The existing stack requires only two new Python packages to support the full AI audit pipeline: `spacy>=3.7.0` (for Named Entity Recognition to detect brand mentions) and `rapidfuzz>=3.6.0` (for fuzzy brand name matching catching abbreviations and typos). LiteLLM is already installed at version 1.80.7 and provides a unified `completion()` interface for ChatGPT, Claude, and Perplexity through a single call pattern -- the `optimizer.py` should be migrated away from the direct `openai` SDK to use LiteLLM. Three dead dependencies (langchain, langchain-openai, sentence-transformers) should be removed from requirements.txt as they are listed but not installed. One new environment variable (`PERPLEXITY_API_KEY`) and several configuration constants (query limits, timeouts, model names, cost caps) need to be added to `config.py`.

See `.planning/research/STACK.md` for complete dependency list, model selection rationale, and cost estimates.

**Core technologies:**
- **LiteLLM 1.80.7** (already installed): Unified gateway for OpenAI, Anthropic, Perplexity -- eliminates per-provider SDK management and provides built-in cost tracking per call
- **spaCy + en_core_web_sm**: Named Entity Recognition for brand/organization mention detection -- deterministic, millisecond-speed, far cheaper than LLM-based extraction at audit scale
- **rapidfuzz**: Fuzzy string matching catching brand name variants (abbreviations, misspellings, partial names) -- 10-100x faster than fuzzywuzzy (C++ backend)
- **Redis (existing)**: Response caching keyed by `sha256(query + engine)` with 24h TTL -- the primary cost control mechanism
- **Celery (existing)**: Async audit pipeline execution -- already in docker-compose but not yet wired to analysis; this is the right time to wire it properly
- **pgvector (existing)**: Semantic comparison between AI's description of the brand and the site's own content (messaging alignment score)

### Expected Features

Research confirms the following feature prioritization from the competitive landscape and dependency analysis.

See `.planning/research/FEATURES.md` for full feature table with complexity, confidence, and cost impact assessments.

**Must have (Phase 1 -- Core Audit Loop):**
- Site crawl + AI-readiness signal extraction -- already partially built; foundation for query generation
- Auto query generation from site content (DF-6) -- THE differentiator; enables zero-config URL-first onboarding
- Multi-engine AI querying: ChatGPT + Claude + Perplexity minimum (TS-1) -- this is the product
- Brand mention detection with verbatim quotes (TS-2) -- core output; without quotes there is no proof
- Visibility score 0-100 (TS-3) -- the metric users track and report
- Per-query drill-down with full AI response (DF-5) -- low complexity, high value

**Must have (Phase 2 -- Competitive Intelligence):**
- Competitor comparison / gap analysis (TS-4) -- makes the audit actionable; who IS being mentioned?
- Query/prompt management: review, edit, add custom queries (TS-5)
- Actionable recommendations (TS-7) -- even basic ones dramatically increase perceived value
- Dashboard with score overview (TS-6)

**Defer (Phase 3+):**
- Query history over time / trend tracking (TS-9) -- natural launch of monitoring tier
- PDF/CSV export for agencies (TS-8) -- important but not blocking
- Sentiment analysis per mention (DF-2)
- Contextual mention analysis (DF-3) -- recommendation vs. warning vs. comparison
- Multi-brand agency management (DF-7)
- Source attribution tracking from Perplexity citations (DF-8)
- AI content gap identification (DF-4) -- expensive LLM analysis, defer until unit economics understood
- Content-level recommendations (DF-9) -- most expensive feature; defer until audit loop proven

**Defer indefinitely (Anti-features to avoid):**
- Real-time continuous monitoring (builds before the audit is reliable)
- Content rewriting / AI writing tool (scope creep into a different product category)
- Traditional SEO metrics (competing with Ahrefs/Semrush is a losing battle)
- Social media monitoring (muddies the value proposition)
- Browser extension (engineering distraction)
- AI chatbot assistant (if the dashboard requires a chatbot to interpret, the UX needs work)

### Architecture Approach

The AI audit system adds three major subsystems to the existing 4-layer FastAPI architecture (routers, services, models, tasks) without disrupting what works. The core pattern is an async 5-phase pipeline orchestrated by Celery: (1) site crawl using existing BeautifulSoup/Playwright infrastructure, (2) LLM-based query generation from crawled context, (3) parallel AI engine dispatch via asyncio.gather with per-engine semaphores, (4) brand mention extraction via spaCy + rapidfuzz + pgvector alignment scoring, (5) composite GEO score computation (site readiness 30% + AI presence 70%). New tables (audits, audit_queries, ai_engine_responses, brand_mentions, site_crawl_results) are clean additions that do not alter the existing analyses table. The existing analyses table and AnalyzerService stay in place for backward compatibility but are not extended.

See `.planning/research/ARCHITECTURE.md` for complete component designs, data flow diagrams, database schema, build order, and code patterns.

**Major components:**
1. **AuditOrchestrator** -- Thin coordinator wiring all services together; Celery task entry point; manages audit status progression across 6 states
2. **QueryGenerator** -- Crawls the URL using existing BeautifulSoup infrastructure; extracts brand, industry, product, competitor signals; calls LLM once to generate 10-15 categorized queries (industry, brand-direct, comparison, problem, recommendation)
3. **AIEngineOrchestrator** -- Parallel dispatch via asyncio.gather + per-engine asyncio.Semaphore for rate limiting; Redis cache check before each API call; return_exceptions=True so one engine failure does not block others
4. **Engine Adapters** (OpenAI, Anthropic, Perplexity) -- Thin wrappers with engine-specific prompt handling, response parsing, retry logic via tenacity; registered in ENGINE_REGISTRY for easy addition of Gemini/Copilot later
5. **ResponseAnalyzer** -- spaCy NER to find organization entities; rapidfuzz to match against target brand + competitors; pgvector cosine similarity for messaging alignment; LLM fallback only for ambiguous cases
6. **ScoringPipeline** -- Two-dimensional scoring: site readiness (structured data, content quality, AI crawler access, authority signals) at 30% weight + AI presence (mention frequency, accuracy, sentiment, competitive position) at 70% weight; starts simple, iterated based on user feedback

### Critical Pitfalls

See `.planning/research/PITFALLS.md` for complete pitfall catalog with phase mappings, warning signs, and detection methods.

1. **API cost explosion without per-audit budget controls (C-1)** -- Model unit economics BEFORE writing any AI query code. Hard cap of N queries per engine at the service layer. Use cheapest models (gpt-4o-mini, claude-3-5-haiku). Cache responses in Redis with 24h TTL. Track `cost_per_audit` from day one. Never expose AI audit endpoints without authentication.

2. **TOS violations: scraping AI UIs instead of using official APIs (C-2)** -- Official APIs only: OpenAI API, Anthropic API, Perplexity pplx-api. The existing Playwright dependency is for crawling user-submitted URLs, NOT for interacting with chat.openai.com or claude.ai. Review current TOS for all three providers before implementation begins. This is an architecture decision that must be locked before any AI integration code is written.

3. **Building monitoring before nailing the one-time audit (C-3)** -- Strict milestone gate: the one-time audit must be validated with real users before any scheduling, trend tracking, or alert code is written. Celery beat must not be configured until Phase 3+. The data model should be monitoring-compatible (timestamps, versioning) without implementing the monitoring layer.

4. **Storing AI responses without data handling strategy (C-4)** -- Review each provider's API terms on output storage and redistribution before the first API response is stored. Store structured extracts (brand_mentioned, context excerpt, sentiment, position) rather than full transcripts. Implement data retention from day one: add `expires_at` column, purge raw text after N days, keep scores and metadata. Flag potential PII (real person names in AI responses).

5. **LLM non-determinism eroding score trust (H-1)** -- Set temperature=0 on all audit queries. Track and store the model version identifier returned in every API response. Design scoring to weight stable binary signals (mentioned/not) higher than fuzzy signals (sentiment, position). Display confidence alongside scores where variance is high. Run baseline queries against known brands to detect model drift.

6. **Over-engineering the scoring algorithm (H-2, validated by existing 108-point system)** -- Start with the simplest meaningful score: `(engines_that_mention_brand / total_engines_queried) * 100`. Layer complexity only when user feedback validates each additional signal. The existing codebase's 108-point system is a concrete cautionary tale: elaborate measurement infrastructure with questionable signal value.

7. **Authentication disabled before AI endpoints exposed (codebase-specific)** -- Authentication must be enabled before any AI audit endpoint is publicly accessible. A single unauthenticated endpoint can drain the entire API budget from automated requests. This is a prerequisite for Phase 1, not a Phase 2 polish item.

## Implications for Roadmap

Based on research, the feature dependency graph and critical pitfall analysis suggest four phases. The critical path is: foundation and safety (auth, models, adapters, cost controls) -> core audit pipeline (crawl, generate, query, analyze, score) -> competitive intelligence and usability (competitor comparison, dashboard, recommendations) -> enrichment and scale features.

### Phase 1: Foundation and Safety

**Rationale:** No AI query code should be written until cost controls, authentication, and the data model are in place. Codebase-specific pitfalls (disabled auth, no outbound rate limiting, .env committed with keys) are blockers, not afterthoughts. This phase makes the system safe to expose before making it functional.
**Delivers:** Authentication enabled; new database schema (audits, audit_queries, ai_engine_responses, brand_mentions, site_crawl_results) with Alembic migration; engine adapter layer (BaseEngineAdapter ABC + OpenAI, Anthropic, Perplexity adapters) with unit tests against real APIs or mocks; Redis cache service for AI responses; per-audit cost tracking instrumentation; outbound rate limiter for AI providers.
**Addresses features:** TS-1 infrastructure (API integration, not yet querying), TS-10 prerequisites
**Avoids pitfalls:** C-1 (cost explosion), C-2 (TOS review happens here), C-4 (data handling strategy defined), H-3 (rate limiting from day one), codebase-specific auth and .gitignore issues
**Research flag:** No additional research needed. Standard Python async patterns + established API patterns.

### Phase 2: Core Audit Pipeline

**Rationale:** Once the foundation is safe, build the full pipeline end-to-end using a vertical slice approach (one URL -> one query -> one engine -> basic scoring) before scaling to multiple queries and engines. This validates the pipeline architecture before investing in parallel execution.
**Delivers:** QueryGenerator (site crawl + LLM-based query generation from crawled context); AIEngineOrchestrator wired to all three engines with parallel dispatch and caching; ResponseAnalyzer (spaCy NER + rapidfuzz brand detection + verbatim quote extraction); ScoringPipeline (simple score: mentions/total_engines * 100, expandable later); AuditOrchestrator Celery task wiring all components; API endpoints (POST /audit/start, GET /audit/{id}, GET /audit/{id}/results); frontend audit initiation UI with progress polling.
**Addresses features:** TS-10 (site crawl), DF-6 (auto query generation), TS-1 (multi-engine querying), TS-2 (mention detection with quotes), TS-3 (visibility score), DF-5 (per-query drill-down with full response)
**Avoids pitfalls:** H-1 (temperature=0, model version logging), H-2 (simple scoring first), H-4 (user-intent queries not brand-name-based), M-1 (engine-specific adapters), M-2 (graceful degradation), M-3 (show queries before executing), L-1 (timeouts on all API calls), L-3 (prompt templates in config not hardcoded)
**Stack used:** LiteLLM (query dispatch), spaCy + rapidfuzz (mention analysis), Redis (response cache), Celery (pipeline orchestration), pgvector (alignment scoring)
**Research flag:** Query template design (H-4) needs validation against known brands before auto-generation feature is built. Test: run audit on Salesforce for CRM queries -- if it surfaces Salesforce consistently, the query design works.

### Phase 3: Competitive Intelligence and Usability

**Rationale:** The core audit loop (Phase 2) must be validated with real users before expanding to competitive analysis and recommendations. Competitor comparison multiplies API cost by 3-5x (one pipeline run per competitor). This phase converts the raw audit into an actionable intelligence product.
**Delivers:** Competitor comparison / gap analysis (same pipeline for competitor brands); query management UI (review, edit, add custom queries before executing); basic actionable recommendations (even generic ones dramatically increase perceived value); dashboard with score overview (per-engine breakdown, trend direction, top issues); export to PDF/CSV for agency reporting.
**Addresses features:** TS-4 (competitor comparison), TS-5 (query management), TS-7 (recommendations), TS-6 (dashboard), TS-8 (export)
**Avoids pitfalls:** C-1 (competitor queries must count against the per-audit budget cap), C-3 (monitoring boundary explicitly enforced -- no scheduling code)
**Research flag:** Recommendations content requires subject matter judgment on what GEO optimization actions are most impactful. May need a focused research spike on GEO best practices before writing recommendation templates.

### Phase 4: Enrichment and Advanced Features

**Rationale:** Once the audit is proven valuable with real users and the unit economics are understood, add enrichment layers that increase depth without changing the core value proposition. Monitoring tier launches here as the natural revenue upsell.
**Delivers:** Sentiment analysis per mention (DF-2); contextual mention classification -- recommendation vs. comparison vs. warning (DF-3); source attribution tracking from Perplexity citations (DF-8); query history over time / trend tracking (TS-9); multi-brand management for agencies (DF-7); monitoring tier with scheduled re-audits (unlocks AF-1 anti-feature properly, as paid upgrade after core is solid).
**Addresses features:** TS-9, DF-2, DF-3, DF-7, DF-8
**Avoids pitfalls:** C-3 (monitoring only starts here, after Phase 2 is validated), M-4 (re-scoring capability; raw data preserved from Phase 1, scoring version field added in Phase 1 schema)
**Research flag:** Multi-brand agency management and monitoring tier both need research-phase before planning (rate limiting strategy per customer tier, OpenAI Batch API for 50% cost discount on scheduled jobs, Celery beat configuration).

### Phase Ordering Rationale

- **Safety before functionality:** Authentication disabled + no cost controls = existential financial risk. These prerequisites cannot be deferred to a polish phase.
- **Vertical slice before horizontal expansion:** Build one complete audit path (one URL, one query, one engine, basic scoring) end-to-end in Phase 2 before scaling. This validates the Celery task boundary, async patterns, and API response storage before committing to the full architecture.
- **Core audit before competitive analysis:** TS-4 (competitor comparison) depends on TS-1 and TS-2 being reliable. Running unreliable audits against competitors produces misleading gap analysis.
- **Validate before monitoring:** C-3 pitfall is clear -- monitoring garbage is worse than no monitoring. The monitoring tier only launches after the one-time audit is validated.
- **Dependencies drive grouping:** The feature dependency graph (FEATURES.md) confirms the Phase 1-2 grouping. TS-10 -> DF-6 -> TS-1 -> TS-2 -> TS-3 is the critical path. Everything else layers on top.

### Research Flags

Phases needing deeper research during planning:
- **Phase 2 (Query design):** The user-intent query template set needs validation against real brands before the auto-generation feature is built. Test prompts against Salesforce (CRM), Nike (footwear), and a smaller brand before finalizing template structure.
- **Phase 3 (Recommendations):** GEO optimization best practices need a focused research spike to produce recommendation templates that are actually actionable, not generic SEO advice repackaged.
- **Phase 4 (Monitoring tier + agency features):** OpenAI Batch API availability and pricing (claimed 50% discount, MEDIUM confidence), Celery beat configuration for scheduled jobs, rate limiting strategy per customer tier.

Phases with standard patterns (skip additional research):
- **Phase 1 (Foundation):** Standard Python async patterns, SQLAlchemy/Alembic migrations, tenacity retry library. All well-documented.
- **Phase 2 (Pipeline):** asyncio.gather + Semaphore pattern, engine adapters, Redis caching are established patterns with clear implementation guides in ARCHITECTURE.md.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | LiteLLM already installed (1.80.7), spaCy/rapidfuzz are established libraries. Model names and pricing are MEDIUM (verify before implementation). No established open-source GEO library found (LOW confidence; space is nascent). |
| Features | MEDIUM | Competitor feature analysis based on training data (pre-2025). Feature complexity estimates for existing infrastructure are HIGH confidence. Cost estimates are MEDIUM. |
| Architecture | HIGH | Based on direct codebase analysis + established Python async patterns. Schema design is HIGH confidence. Perplexity API specifics are MEDIUM (adapter interface may have evolved). |
| Pitfalls | HIGH for patterns, MEDIUM for specifics | Non-determinism, TOS violations, cost explosion, premature monitoring: HIGH confidence (fundamental properties). Specific rate limit numbers, pricing, current TOS language: MEDIUM (verify against live docs). |

**Overall confidence:** MEDIUM-HIGH

The architectural and product recommendations are HIGH confidence. The specific API pricing, rate limits, model names, and provider TOS language are MEDIUM confidence and require verification against live documentation before Phase 1 implementation begins.

### Gaps to Address

- **API pricing verification:** Estimated cost per audit ($0.03-0.08) is based on early 2025 pricing. Verify current OpenAI, Anthropic, and Perplexity pricing before modeling unit economics. Perplexity uses per-request pricing for some models which changes the cost structure.
- **Perplexity API model names:** `perplexity/sonar` was accurate as of early 2025. Verify current model names and capabilities at https://docs.perplexity.ai before writing the Perplexity adapter.
- **Provider TOS for output storage:** Specifically, whether each provider allows storing and re-displaying API outputs as a product feature. OpenAI generally allows commercial use of API outputs; Perplexity's policy needs verification. This must be resolved before Phase 1 schema design is finalized.
- **OpenAI Batch API availability:** Claimed 50% discount for 24h-window jobs. Was available as of mid-2024; verify it is still offered before designing the Phase 4 monitoring tier around it.
- **Existing codebase concerns from CONCERNS.md:** Six specific issues identified (BackgroundTasks instead of Celery, disabled auth, rate limiter fails open, .env committed, random number fallbacks in scoring, dual ORM architecture) must all be resolved in Phase 1 before any new AI features are built.
- **Open-source GEO library landscape:** Research could not verify whether new Python libraries for AI visibility monitoring launched in late 2025 or 2026. Search before Phase 2 to avoid building something that already exists.

## Sources

### Primary (HIGH confidence)
- Existing codebase analysis: `/home/salim/Informatique/Perso/Endexa/geo-platform-mvp/.planning/codebase/ARCHITECTURE.md`
- Project definition: `/home/salim/Informatique/Perso/Endexa/geo-platform-mvp/.planning/PROJECT.md`
- `CLAUDE.md` and `docs/` directory (direct codebase audit): existing stack, installed packages, CONCERNS.md issues
- LiteLLM installed at 1.80.7 (verified in venv)
- Python asyncio.Semaphore and asyncio.gather: Python standard library documentation
- tenacity retry library: established Python ecosystem library, well-documented
- spaCy: established NLP library, well-documented for NER tasks
- rapidfuzz vs fuzzywuzzy benchmarks: established benchmark results

### Secondary (MEDIUM confidence)
- Competitor feature landscape (Profound, Otterly.ai, Peec AI, Knowatoa): training data knowledge as of early 2025 -- features and pricing may have changed
- LiteLLM provider support for Perplexity: training data (confirmed support exists, model name needs verification)
- OpenAI, Anthropic, Perplexity API pricing: training data as of early 2025 (verify before modeling unit economics)
- API rate limit structures: training data (verify current tier limits before implementation)
- Provider TOS on API output storage: training data (must be verified against current policy documents before implementation)

### Tertiary (LOW confidence)
- Open-source GEO monitoring library landscape: training data only; space is nascent and evolving rapidly; new libraries may have launched in late 2025 or 2026 -- search before Phase 2
- Cost-per-audit estimates ($0.03-0.08): calculated from training-data pricing; verify against current pricing before using for business decisions
- OpenAI Batch API 50% discount: was available as of mid-2024; verify current availability and pricing

---
*Research completed: 2026-02-21*
*Ready for roadmap: yes*
