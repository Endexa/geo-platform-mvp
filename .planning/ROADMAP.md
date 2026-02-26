# Roadmap: Endexa GEO Platform v2

## Overview

Endexa v2 is a brownfield rebuild: the FastAPI + Celery + Redis + Supabase foundation works, but the scoring pipeline (103/108 data points return zeros), recommendations engine (stub), AI visibility (fabricated), and dashboard (fake data) must all be rebuilt from scratch. The roadmap follows a strict dependency chain: real scores first (everything depends on them), then features that consume scores (recommendations, visibility, exports), then monetization and interactive features, then polish. Every phase delivers a coherent, verifiable capability that the next phase builds on.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Scoring Foundation** - All 61 criteria produce real measurements; dead code removed; integration-tested against known sites
- [x] **Phase 2: Recommendations + Competitor Benchmarking** - Deterministic gap analysis generates prioritized, actionable recommendations; auto-competitor discovery and side-by-side comparison
- [x] **Phase 3: AI Visibility Hardening** - Statistical multi-query measurement replaces single-shot checks; per-engine breakdown with confidence indicators
- [x] **Phase 4: Payments + Freemium Gating** - Stripe checkout flow, webhook handling, subscription lifecycle, tier-based feature gating
- [x] **Phase 5: Reports + Exports** - PDF/HTML audit reports and Jira-compatible CSV export with customizable fields
- [x] **Phase 6: Chat Assistant** - SSE-streamed LLM chat grounded in user's actual audit data
- [x] **Phase 7: Dashboard + Frontend Polish** - Real metrics dashboard with trend charts, audit history, multi-site management, and production-ready UI throughout
- [x] **Phase 8: Code Analysis** - Prompt generation for user's codebase, output ingestion, enriched recommendations from code findings

## Phase Details

### Phase 1: Scoring Foundation
**Goal**: Users receive real, trustworthy audit scores derived from actual page measurements -- not zeros or fabricated numbers
**Depends on**: Nothing (critical path root)
**Requirements**: SCORE-01, SCORE-02, SCORE-03, SCORE-04, SCORE-05, SCORE-06, SCORE-07, SCORE-08, SCORE-09, SCORE-10
**Success Criteria** (what must be TRUE):
  1. Running an audit on a known site (e.g., stripe.com) produces non-zero scores across all 4 categories (Crawlability, Content Structure, Structured Data, Authority) with scores that a human SEO professional would consider reasonable
  2. Every criterion that cannot be measured for a given page reports NOT_MEASURED or NOT_APPLICABLE -- never a fabricated value or hardcoded zero
  3. The Optimization Score aggregates correctly via the weakest-link formula (0.6 * mean + 0.4 * min) and the dual-score display (Visibility + Optimization) renders on the audit results page
  4. The legacy `geo_data_points/` directory is deleted and no imports reference it
  5. Integration tests run a full audit against a known test site and verify that output scores fall within expected ranges
**Plans**: 2 plans

Plans:
- [x] 01-01-PLAN.md -- Fix scoring bugs (C9 fabricated score, link discovery field, Playwright cleanup) and delete legacy dead code
- [x] 01-02-PLAN.md -- Integration tests for all scorers, aggregation verification, and dual-score display confirmation

### Phase 2: Recommendations + Competitor Benchmarking
**Goal**: Users receive specific, prioritized recommendations they can immediately act on, with competitor context showing where they stand relative to discovered competitors
**Depends on**: Phase 1
**Requirements**: REC-01, REC-02, REC-03, REC-04, REC-05, COMP-01, COMP-02, COMP-03, COMP-04
**Success Criteria** (what must be TRUE):
  1. After an audit completes, the user sees a prioritized list of recommendations grouped by category with severity levels, where each recommendation includes a clear action description, impact estimate, and evidence from the actual audit data
  2. Recommendations are industry-aware: a SaaS site does not receive advice about LocalBusiness schema, and a blog does not receive advice about Product schema
  3. Competitor brands are automatically discovered from AI engine responses (NER extraction) and displayed in a side-by-side score comparison without the user manually entering competitor URLs
  4. Share of voice (percentage of AI mentions per brand across engines) is calculated and displayed per audit
  5. Competitor data persists across audits so users can track competitive positioning over time
**Plans**: 3 plans

Plans:
- [x] 02-01-PLAN.md -- Vertical classifier + recommendation engine enhancements (industry-aware filtering, impact delta calculation)
- [x] 02-02-PLAN.md -- Cross-audit competitor persistence (brand linking, SOV trend tracking)
- [x] 02-03-PLAN.md -- Pipeline wiring + integration tests (audit_tasks.py integration, end-to-end verification)

### Phase 3: AI Visibility Hardening
**Goal**: Users can trust their AI Visibility Score because it is derived from statistical measurement across multiple queries and engines, not a single-shot check
**Depends on**: Phase 1
**Requirements**: VIS-01, VIS-02, VIS-03, VIS-04
**Success Criteria** (what must be TRUE):
  1. AI Visibility Score is derived from multiple real LLM queries per engine (5-15 queries each) with mention rates and confidence indicators shown to the user
  2. Per-engine breakdown displays separate visibility scores for each active engine (ChatGPT, Claude, Perplexity, Gemini)
  3. Engines without API keys are gracefully skipped, and the overall score adjusts to reflect only engines that were actually queried
  4. Running the same audit twice within the cache TTL produces consistent results (not random fluctuation)
**Plans**: 2 plans

Plans:
- [x] 03-01-PLAN.md -- Backend: enhanced VisibilityScore model, Alembic migration, enriched ScoringService with per-engine statistical breakdown, API schema with backward compatibility
- [x] 03-02-PLAN.md -- Frontend: per-engine cards with confidence badges and skipped-engine display + integration tests for enhanced scoring pipeline

### Phase 4: Payments + Freemium Gating
**Goal**: Users can start with a free partial audit and upgrade to a paid subscription for full access, with Stripe handling the payment flow
**Depends on**: Phases 1-2 (must know what features to gate)
**Requirements**: PAY-01, PAY-02, PAY-03, PAY-04, PAY-05
**Success Criteria** (what must be TRUE):
  1. A non-paying user can run a free audit that shows Crawlability category scores, overall score, and top 3 recommendations -- but cannot access full category breakdowns, all recommendations, exports, chat, or code analysis
  2. Clicking "Upgrade" initiates a Stripe Checkout Session that successfully processes a test payment and creates a subscription
  3. Stripe webhooks correctly handle subscription lifecycle events (created, updated, cancelled, payment failed) and the user's access level updates accordingly
  4. Feature gating is enforced server-side via FastAPI dependencies -- accessing a paid endpoint without a subscription returns a clear "upgrade required" response
**Plans**: 2 plans

Plans:
- [x] 04-01-PLAN.md -- Subscription model, StripeService, payments API (checkout, portal, webhook, session-status)
- [x] 04-02-PLAN.md -- Feature gating dependencies, tier-aware audit/recommendation endpoints, pricing page, checkout flow, tests

### Phase 5: Reports + Exports
**Goal**: Users can download professional audit reports and export recommendations to their project management tools
**Depends on**: Phases 1-2 (needs real scores and recommendations)
**Requirements**: RPT-01, RPT-02, RPT-03, RPT-04
**Success Criteria** (what must be TRUE):
  1. User can download a PDF audit report containing executive summary, dual scores, per-category breakdown, top recommendations, and charts
  2. User can download an HTML version of the same report that renders correctly in a browser
  3. User can export recommendations as a Jira-compatible CSV with customizable fields (grouping, priority, epic link) that imports cleanly into Jira
  4. Report downloads are gated by subscription tier (paid users only)
**Plans**: 2 plans

Plans:
- [x] 05-01-PLAN.md -- ReportService (HTML/PDF generation, CSV export) with tier-gated API endpoints
- [x] 05-02-PLAN.md -- Frontend download buttons, CSV export options, unit tests

### Phase 6: Chat Assistant
**Goal**: Users can ask questions about their audit results in natural language and receive accurate, contextual answers
**Depends on**: Phases 1-2 (needs scores and recommendations as context)
**Requirements**: CHAT-01, CHAT-02, CHAT-03, CHAT-04
**Success Criteria** (what must be TRUE):
  1. User can open a chat interface on any completed audit and ask questions like "Why is my schema score low?" and receive an answer grounded in their actual audit data
  2. Chat responses stream in real-time via SSE (not waiting for full response)
  3. Follow-up questions maintain conversation context -- the user can have a multi-turn discussion about their audit
  4. Chat responses reference specific scores, criteria, and recommendations from the user's audit (not generic advice)
**Plans**: 2 plans

Plans:
- [x] 06-01-PLAN.md -- Backend: ChatSession model, migration, ChatService (context builder + LLM streaming), SSE endpoint with tier gating
- [x] 06-02-PLAN.md -- Frontend: useChat composable, ChatPanel slide-over component, audit page integration, unit tests

### Phase 7: Dashboard + Frontend Polish
**Goal**: Users see a production-quality dashboard with real metrics, trend charts, and audit history -- and the entire application feels polished and professional
**Depends on**: Phases 1-6 (dashboard requires all components producing real data)
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04, DASH-05, UI-01, UI-02, UI-03, UI-04
**Success Criteria** (what must be TRUE):
  1. Dashboard displays real audit history with actual data -- no mock numbers, no placeholder charts
  2. Score trend charts show how Visibility and Optimization scores evolve across multiple audits over time
  3. Per-engine AI visibility breakdown and per-category score breakdown are displayed on the dashboard
  4. Agencies can manage multiple client sites from one account (multi-site management)
  5. The entire application follows the design system (Data-Dense Dashboard style), with proper loading states, error states, empty states, and responsive layout on desktop and tablet
**Plans**: 3 plans

Plans:
- [x] 07-01-PLAN.md -- Design system foundation (Fira fonts, color token standardization) and responsive sidebar layout
- [x] 07-02-PLAN.md -- Dashboard data quality (category breakdown, trend chart improvements, engine display names) and multi-site brand selector
- [x] 07-03-PLAN.md -- Systematic loading/error/empty states across all pages, audit results polish, navigation cleanup

### Phase 8: Code Analysis
**Goal**: Users can get deeper, code-level recommendations by running Endexa-generated prompts on their codebase and uploading the results
**Depends on**: Phases 1-2 (needs scoring gaps to generate relevant prompts)
**Requirements**: CODE-01, CODE-02, CODE-03, CODE-04
**Success Criteria** (what must be TRUE):
  1. After an audit, the user can download analysis prompts tailored to their scoring gaps that they can run with their AI tools (Claude, Copilot, etc.)
  2. User can upload the output from running those prompts back into Endexa
  3. Endexa produces additional, code-specific recommendations based on the uploaded analysis output
  4. Generated prompts are useful for analysis but do not expose Endexa's proprietary scoring logic (users still need Endexa for interpretation)
**Plans**: 2 plans

Plans:
- [x] 08-01-PLAN.md -- Backend: CodeAnalysis + CodeRecommendation models, migration 015, PromptGeneratorService (template-based, no LLM), CodeAnalysisService (LiteLLM structured output), Celery task, all 5 API endpoints
- [x] 08-02-PLAN.md -- Frontend: useCodeAnalysis composable, CodeAnalysisPrompts + CodeAnalysisUpload components, audit.vue integration, 25 backend unit tests

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8
Note: Phases 3 and 4 can execute in parallel (independent dependencies).

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Scoring Foundation | 2/2 | Complete | 2026-02-26 |
| 2. Recommendations + Competitor Benchmarking | 3/3 | Complete | 2026-02-26 |
| 3. AI Visibility Hardening | 2/2 | Complete | 2026-02-26 |
| 4. Payments + Freemium Gating | 2/2 | Complete | 2026-02-26 |
| 5. Reports + Exports | 2/2 | Complete | 2026-02-26 |
| 6. Chat Assistant | 2/2 | Complete | 2026-02-26 |
| 7. Dashboard + Frontend Polish | 3/3 | Complete | 2026-02-26 |
| 8. Code Analysis | 2/2 | Complete | 2026-02-26 |
