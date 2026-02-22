# Roadmap: GEO Platform -- AI Brand Visibility Auditor

## Overview

This roadmap transforms the existing FastAPI + Nuxt 3 + PostgreSQL codebase from a 108-point website scorer into an AI brand visibility auditor. The journey starts with safety (auth and cost controls before any AI API calls), builds the audit pipeline in vertical layers (crawl, query, dispatch, analyze), wraps it in a user-facing audit experience, then layers on competitive intelligence, brand signature analysis, actionable insights, and agency-scale reporting. Nine phases, each delivering a coherent, verifiable capability. Every phase depends on the previous, and no AI endpoint is exposed until the system is safe to operate.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation & Safety** - Enable auth, cost tracking, response caching, and outbound rate limiting before any AI API code
- [ ] **Phase 2: Site Crawl & Query Generation** - Crawl user URLs for AI-readiness signals and auto-generate industry-relevant queries from content
- [ ] **Phase 3: AI Engine Dispatch** - Query ChatGPT, Claude, and Perplexity APIs with generated queries via LiteLLM
- [ ] **Phase 4: Mention Detection & Scoring** - Detect brand mentions in AI responses with verbatim quotes and compute visibility scores
- [ ] **Phase 5: Audit Experience** - Users can trigger an audit from URL entry to scored results with per-query drill-down
- [ ] **Phase 6: Competitive Intelligence** - Compare brand visibility against competitors with gap analysis and custom queries
- [ ] **Phase 7: Brand Signature Analysis** - Compare brand self-image from their website with how AI engines describe them
- [ ] **Phase 8: Insights & Dashboard** - Actionable recommendations, sentiment analysis, and single-screen dashboard overview
- [ ] **Phase 9: Reporting & Scale** - PDF/CSV export, query history for trends, and multi-brand agency management

## Phase Details

### Phase 1: Foundation & Safety
**Goal**: The system is safe to expose to the internet -- authenticated, cost-controlled, and rate-limited -- before any AI API integration code is written
**Depends on**: Nothing (first phase)
**Requirements**: FOUND-01, FOUND-02, FOUND-03, FOUND-04
**Success Criteria** (what must be TRUE):
  1. User can register, log in with email/password, and access protected endpoints with a JWT token
  2. Every outbound AI API call is tracked with cost metadata, and a per-audit budget cap halts execution when exceeded
  3. Identical AI queries return cached responses from Redis within the 24-hour TTL window instead of making new API calls
  4. Outbound requests to each AI engine API are throttled to stay within provider rate limits, with back-pressure when limits are hit
  5. Unauthenticated requests to any audit-related endpoint receive a 401 response
**Plans**: 3 plans

Plans:
- [x] 01-01-PLAN.md -- Dependency migration (PyJWT, pwdlib), Alembic setup, auth endpoints (FOUND-01)
- [x] 01-02-PLAN.md -- Cost tracking model, service, and Celery initialization (FOUND-02)
- [x] 01-03-PLAN.md -- Redis AI cache service, outbound rate limiter, enable auth on endpoints (FOUND-03, FOUND-04)

### Phase 2: Site Crawl & Query Generation
**Goal**: The system can take any URL, extract AI-readiness signals from the site, and generate a set of industry-relevant queries that a real user would ask an AI engine about that brand's domain
**Depends on**: Phase 1
**Requirements**: AUDIT-02, AUDIT-03
**Success Criteria** (what must be TRUE):
  1. Given a URL, the system crawls the site and extracts structured data (schema.org, robots.txt AI directives, content structure, authority markers)
  2. From crawled content, the system generates 10-15 categorized queries (industry, brand-direct, comparison, problem, recommendation) that reflect how real users would ask AI about that domain
  3. Generated queries are stored and associated with an audit record for downstream processing
**Plans**: 2 plans

Plans:
- [ ] 02-01-PLAN.md -- Audit/AuditQuery models, Alembic migration 003, CrawlerService with AI-readiness signal extraction (AUDIT-02)
- [ ] 02-02-PLAN.md -- QueryGeneratorService with LiteLLM structured output, Celery audit pipeline, audit API endpoints (AUDIT-03)

### Phase 3: AI Engine Dispatch
**Goal**: The system can send generated queries to ChatGPT, Claude, and Perplexity in parallel and store their responses reliably, with graceful degradation if one engine fails
**Depends on**: Phase 2
**Requirements**: AUDIT-04
**Success Criteria** (what must be TRUE):
  1. Each generated query is dispatched to all three AI engines (ChatGPT, Claude, Perplexity) via LiteLLM with engine-specific adapters
  2. Engine queries execute in parallel with per-engine semaphores respecting rate limits, and a single engine failure does not block the others
  3. Every AI response is stored with its full text, model version identifier, cost metadata, and timestamp
  4. Cached responses are served for duplicate query+engine combinations within the 24h TTL
**Plans**: TBD

Plans:
- [ ] 03-01: TBD
- [ ] 03-02: TBD

### Phase 4: Mention Detection & Scoring
**Goal**: The system can analyze AI responses to detect whether and how a brand is mentioned, extract verbatim quotes, and compute a meaningful visibility score
**Depends on**: Phase 3
**Requirements**: AUDIT-05, AUDIT-06
**Success Criteria** (what must be TRUE):
  1. The system detects brand name mentions (including abbreviations, typos, and variants) in AI engine responses using NER and fuzzy matching
  2. Each detected mention includes a verbatim quote of the surrounding context from the AI response
  3. A visibility score (0-100) is computed with a per-engine breakdown showing which engines mention the brand and how prominently
  4. Score computation uses temperature=0 on all queries and logs model version for reproducibility
**Plans**: TBD

Plans:
- [ ] 04-01: TBD
- [ ] 04-02: TBD

### Phase 5: Audit Experience
**Goal**: A user can enter a URL on the frontend, trigger a complete audit, watch it progress, and explore the scored results with full AI response drill-down
**Depends on**: Phase 4
**Requirements**: AUDIT-01, AUDIT-07
**Success Criteria** (what must be TRUE):
  1. User enters a URL on the frontend and triggers a full AI brand visibility audit with one action
  2. The audit runs asynchronously (Celery) with the frontend polling and displaying progress through crawl, query generation, AI dispatch, analysis, and scoring stages
  3. User sees final results: visibility score, per-engine breakdown, and list of queries with mention/no-mention indicators
  4. User can drill down into any individual query to see the full AI response from each engine with brand mentions highlighted in context
**Plans**: TBD

Plans:
- [ ] 05-01: TBD
- [ ] 05-02: TBD
- [ ] 05-03: TBD

### Phase 6: Competitive Intelligence
**Goal**: Users can compare their brand visibility against competitors and discover what competitors get mentioned for that they do not
**Depends on**: Phase 5
**Requirements**: COMP-01, COMP-02, COMP-03, COMP-04
**Success Criteria** (what must be TRUE):
  1. User can add one or more competitor brand names to an audit for side-by-side comparison
  2. The system runs the same query set against competitor brands and shows a gap analysis: topics where competitors are mentioned but the user's brand is not
  3. User can add, edit, and remove custom queries alongside the auto-generated ones before or after an audit runs
  4. For AI responses that cite sources (especially Perplexity), the system extracts and displays which URLs/sources each engine references
  5. Competitor queries count against the same per-audit budget cap and respect the same rate limits
**Plans**: TBD

Plans:
- [ ] 06-01: TBD
- [ ] 06-02: TBD
- [ ] 06-03: TBD

### Phase 7: Brand Signature Analysis
**Goal**: Users can see the gap between how their brand presents itself and how AI engines actually describe them
**Depends on**: Phase 5 (needs AI responses and site crawl data)
**Requirements**: BRAND-01, BRAND-02, BRAND-03
**Success Criteria** (what must be TRUE):
  1. The system extracts the brand's self-positioning from their website: messaging, values, key claims, and tone
  2. The system compares brand self-image with how AI engines describe them using semantic similarity (pgvector) and keyword analysis
  3. User sees specific mismatches between brand identity and AI perception with concrete examples (e.g., "You say 'premium artisan', AI says 'budget alternative'")
**Plans**: TBD

Plans:
- [ ] 07-01: TBD
- [ ] 07-02: TBD

### Phase 8: Insights & Dashboard
**Goal**: Users get a single-screen overview of their AI visibility with actionable recommendations for improvement and sentiment context for every mention
**Depends on**: Phase 6, Phase 7 (needs competitive data and brand analysis for complete recommendations)
**Requirements**: INSIGHT-01, INSIGHT-02, INSIGHT-03
**Success Criteria** (what must be TRUE):
  1. The system generates actionable recommendations explaining what to fix and why, based on audit findings, competitive gaps, and brand mismatches
  2. A dashboard shows a single-screen overview: visibility score, per-engine breakdown, top issues, and competitive position
  3. Each AI mention is classified by sentiment (positive, negative, neutral) and the sentiment breakdown is visible in the results
  4. Recommendations are prioritized by estimated impact on AI visibility
**Plans**: TBD

Plans:
- [ ] 08-01: TBD
- [ ] 08-02: TBD
- [ ] 08-03: TBD

### Phase 9: Reporting & Scale
**Goal**: Agencies can export audit results for clients, track brand visibility over time, and manage multiple brands under one account
**Depends on**: Phase 8
**Requirements**: REPORT-01, REPORT-02, REPORT-03
**Success Criteria** (what must be TRUE):
  1. User can export a complete audit report as PDF or CSV including scores, mentions, gaps, recommendations, and brand analysis
  2. The system stores query history across audits so users can see how their visibility score and mention patterns change over time
  3. Agency users can create and manage multiple brands under one account, each with separate audit history and tracking
  4. Multi-brand view shows a summary dashboard comparing visibility scores across all managed brands
**Plans**: TBD

Plans:
- [ ] 09-01: TBD
- [ ] 09-02: TBD
- [ ] 09-03: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8 -> 9

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation & Safety | 3/3 | Complete | 2026-02-22 |
| 2. Site Crawl & Query Generation | 0/2 | Not started | - |
| 3. AI Engine Dispatch | 0/2 | Not started | - |
| 4. Mention Detection & Scoring | 0/2 | Not started | - |
| 5. Audit Experience | 0/3 | Not started | - |
| 6. Competitive Intelligence | 0/3 | Not started | - |
| 7. Brand Signature Analysis | 0/2 | Not started | - |
| 8. Insights & Dashboard | 0/3 | Not started | - |
| 9. Reporting & Scale | 0/3 | Not started | - |
