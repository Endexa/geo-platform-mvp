# Roadmap: GEO Platform -- AI Brand Visibility Auditor

## Overview

This roadmap transforms the existing FastAPI + Nuxt 3 + PostgreSQL codebase into a comprehensive GEO+SEO audit platform. The journey starts with safety (auth and cost controls), builds the AI audit pipeline (crawl, query, dispatch, analyze, display), then layers on page-level scoring with research-backed criteria, auto-competitor discovery from AI responses, evidence-based recommendations, and agency-scale reporting. Ten phases, each delivering a coherent, verifiable capability. Every phase depends on the previous.

**Reworked 2026-02-22:** Phases 6-10 redesigned from deep research into GEO scoring methods, AI citation factors, competitor tools, and AI-ready standards. Key changes: Brand Signature deferred to v2. Site AI-Readiness Scoring (page-level criteria checks) added as Phase 6. Competitors auto-discovered from AI responses instead of manually added. Recommendations now evidence-based with research data. Scoring services built from scratch based on research and industry standards (legacy `geo_data_points/` system not used -- incompatible architecture and outdated criteria).

**Research basis:** `.planning/research/` contains 4 research documents informing phases 6-10:
- `geo-scoring-methods.md` -- Princeton GEO paper, Otterly/HubSpot/Evertune methodologies, scoring formulas
- `ai-citation-factors.md` -- Ahrefs 75K-brand study, Surfer SEO 46M-citation analysis, 5-tier factor hierarchy
- `geo-competitors.md` -- 17 competitor deep dives, pricing landscape, market gaps
- `ai-ready-standards.md` -- llms.txt spec, all AI bot user-agents, schema.org tiers, WebMCP

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation & Safety** - Enable auth, cost tracking, response caching, and outbound rate limiting before any AI API code
- [x] **Phase 2: Site Crawl & Query Generation** - Crawl user URLs for AI-readiness signals and auto-generate industry-relevant queries from content
- [x] **Phase 3: AI Engine Dispatch** - Query ChatGPT, Claude, Perplexity, and Gemini APIs with generated queries via LiteLLM
- [x] **Phase 4: Mention Detection & Scoring** - Detect brand mentions in AI responses with verbatim quotes and compute visibility scores
- [x] **Phase 5: Audit Experience** - Users can trigger an audit from URL entry to scored results with per-query drill-down
- [ ] **Phase 6: Site AI-Readiness Scoring** - Score each page against research-backed SEO+GEO criteria with purpose-built scoring services, producing an Optimization Score alongside the Visibility Score
- [x] **Phase 7: Auto-Competitor Discovery** - Extract competitors from AI responses, crawl their sites, and compare technical setup (completed 2026-02-22)
- [ ] **Phase 8: Actionable Recommendations** - Generate page-specific, evidence-based fix recommendations with impact estimates
- [ ] **Phase 9: Dashboard & Reporting** - Combined GEO Score dashboard, competitive position map, PDF/CSV export, audit history
- [ ] **Phase 10: Scale & Agency** - Multi-brand management with per-brand audit history and cross-brand comparison

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
- [x] 02-01-PLAN.md -- Audit/AuditQuery models, Alembic migration 003, CrawlerService with AI-readiness signal extraction (AUDIT-02)
- [x] 02-02-PLAN.md -- QueryGeneratorService with LiteLLM structured output, Celery audit pipeline, audit API endpoints (AUDIT-03)

### Phase 3: AI Engine Dispatch
**Goal**: The system can send generated queries to ChatGPT, Claude, Perplexity, and Gemini in parallel and store their responses reliably, with graceful degradation if one engine fails
**Depends on**: Phase 2
**Requirements**: AUDIT-04
**Success Criteria** (what must be TRUE):
  1. Each generated query is dispatched to all configured AI engines via LiteLLM with engine-specific adapters
  2. Engine queries execute in parallel with per-engine semaphores respecting rate limits, and a single engine failure does not block the others
  3. Every AI response is stored with its full text, model version identifier, cost metadata, and timestamp
  4. Cached responses are served for duplicate query+engine combinations within the 24h TTL
**Plans**: 2 plans

Plans:
- [x] 03-01-PLAN.md -- EngineResponse model, migration 004, dispatch config, DispatchService with parallel engine dispatch (AUDIT-04)
- [x] 03-02-PLAN.md -- Extend Celery pipeline with dispatch stage, update audit API/schemas for engine responses (AUDIT-04)

### Phase 4: Mention Detection & Scoring
**Goal**: The system can analyze AI responses to detect whether and how a brand is mentioned, extract verbatim quotes, and compute a meaningful visibility score
**Depends on**: Phase 3
**Requirements**: AUDIT-05, AUDIT-06
**Success Criteria** (what must be TRUE):
  1. The system detects brand name mentions (including abbreviations, typos, and variants) in AI engine responses using NER and fuzzy matching
  2. Each detected mention includes a verbatim quote of the surrounding context from the AI response
  3. A visibility score (0-100) is computed with a per-engine breakdown showing which engines mention the brand and how prominently
  4. Score computation uses temperature=0 on all queries and logs model version for reproducibility
**Plans**: 2 plans

Plans:
- [x] 04-01-PLAN.md -- BrandMention/VisibilityScore models, migration 005, MentionDetectorService, ScoringService (AUDIT-05, AUDIT-06)
- [x] 04-02-PLAN.md -- Celery ANALYZING pipeline stage, audit API/schemas for mentions and scores (AUDIT-05, AUDIT-06)

### Phase 5: Audit Experience
**Goal**: A user can enter a URL on the frontend, trigger a complete audit, watch it progress, and explore the scored results with full AI response drill-down
**Depends on**: Phase 4
**Requirements**: AUDIT-01, AUDIT-07
**Success Criteria** (what must be TRUE):
  1. User enters a URL on the frontend and triggers a full AI brand visibility audit with one action
  2. The audit runs asynchronously (Celery) with the frontend polling and displaying progress through crawl, query generation, AI dispatch, analysis, and scoring stages
  3. User sees final results: visibility score, per-engine breakdown, and list of queries with mention/no-mention indicators
  4. User can drill down into any individual query to see the full AI response from each engine with brand mentions highlighted in context
**Plans**: 2 plans

Plans:
- [x] 05-01-PLAN.md -- Frontend auth foundation: remove Supabase, useApiFetch/useAuth composables, login page rewrite, auth-aware layout (AUDIT-01)
- [x] 05-02-PLAN.md -- Audit page with URL form, progress polling, results display, query drill-down with highlighted mentions (AUDIT-01, AUDIT-07)

### Phase 6: Site AI-Readiness Scoring
**Goal**: The system scores each crawled page against research-backed SEO+GEO criteria, producing per-page and per-category scores that roll up into an Optimization Score (0-100) displayed alongside the existing Visibility Score
**Depends on**: Phase 5 (needs crawled page data and working audit pipeline)
**Requirements**: READY-01, READY-02, READY-03, READY-04, READY-05, READY-06

**Architecture**: Purpose-built scoring services integrated into the existing audit pipeline. Each scoring category (Crawlability, Content Structure, Structured Data, Authority) is implemented as an async service in `backend/app/services/scoring/` that receives crawled page data and returns per-criteria scores. Services run in the Celery pipeline as a new SCORING stage after ANALYZING. Criteria are derived from research (Princeton GEO paper, Ahrefs 75K study, Surfer SEO 46M analysis, BrightEdge data) and industry standards, NOT from the legacy `geo_data_points/` system (which uses incompatible sync patterns, a separate DB, and outdated criteria).

**Scoring Formula** (research-backed weights):
```
Optimization Score = (
  Crawlability    x 0.25 +    # Can AI bots read this page?
  Content_Structure x 0.25 +  # Is content extractable by AI?
  Structured_Data x 0.20 +    # Schema.org quality
  Authority       x 0.15 +    # E-E-A-T + entity signals + SEO fundamentals
  AI_Visibility   x 0.15      # Actual mention score from phases 4-5
) x 100
```

**Evidence for weights:**
- Crawlability 25%: "If AI can't read your content, nothing else matters" (Otterly.ai core finding). AI crawlers don't execute JS.
- Content Structure 25%: Answer-first format +40% citations (Princeton GEO paper). Clear headings 2.8x citation rate.
- Structured Data 20%: JSON-LD 2.3-2.5x more likely in AI Overviews. FAQPage +28% citations (Frase.io). 3.2x citation rate (BrightEdge).
- Authority 15%: Brand authority is #1 predictor (Ahrefs 75K study, YouTube mentions r=0.737). E-E-A-T r=0.81 correlation with citation.
- AI Visibility 15%: Direct measurement from our audit pipeline (phases 4-5).

**Criteria by Category** (all built from scratch based on research):

#### Category 1: Crawlability (25%) -- READY-01
*Can AI crawlers access and read the page content?*
*Service: `backend/app/services/scoring/crawlability_scorer.py`*

| # | Criteria | Research Impact |
|---|----------|-----------------|
| C1 | GPTBot access (robots.txt) | Required for ChatGPT citations |
| C2 | ClaudeBot access (robots.txt) | Required for Claude citations |
| C3 | PerplexityBot access (robots.txt) | Required for Perplexity citations |
| C4 | OAI-SearchBot access (robots.txt) | Search vs training crawler distinction (OpenAI) |
| C5 | Claude-SearchBot access (robots.txt) | Search vs training crawler distinction (Anthropic) |
| C6 | Bingbot access (robots.txt) | Powers Bing Copilot citations |
| C7 | CCBot access (robots.txt) | Feeds LLaMA/Mistral training data |
| C8 | Google-Extended access (robots.txt) | Controls Gemini training access |
| C9 | SSR detection (JS vs no-JS content diff) | CRITICAL: AI bots don't execute JS |
| C10 | Response time (TTFB) | Slow pages = AI bot timeout/skip |
| C11 | HTTP status code for AI bots | Must respond 200 OK |
| C12 | Resource blockage (CSS/JS in robots.txt) | Blocked resources degrade rendering |

#### Category 2: Content Structure (25%) -- READY-02
*Is the content structured for AI extraction?*
*Service: `backend/app/services/scoring/content_structure_scorer.py`*

| # | Criteria | Research Impact |
|---|----------|-----------------|
| CS1 | Heading hierarchy quality (H1>H2>H3) | 2.8x citation rate with clean hierarchy |
| CS2 | Answer-first format detection | +40% citations (Princeton GEO paper) |
| CS3 | Paragraph length (2-4 sentences ideal) | Short paragraphs = cleaner AI extraction |
| CS4 | Data density (tables, lists, statistics) | 4.1x more citations with data tables (Surfer SEO) |
| CS5 | FAQ section presence | FAQs mirror how users query AI engines |
| CS6 | Content length (1200-1800 words optimal) | Optimal range for AI extraction depth |
| CS7 | Readability score (Flesch-Kincaid 8-10) | AI prefers clear, accessible text |
| CS8 | Citation/reference presence | +20-30% visibility (Princeton GEO paper) |
| CS9 | Content freshness (date signals) | 85% of AI citations from content <2 years old |
| CS10 | Statistics density | +40% visibility boost (Princeton GEO paper) |
| CS11 | Quotation presence (expert quotes) | +15-25% boost (Princeton GEO paper) |
| CS12 | Entity density (named entities/100 words) | Higher entity density = better AI understanding |
| CS13 | Sentence length variety | Variety signals editorial quality |

#### Category 3: Structured Data (20%) -- READY-03
*Schema.org quality and coverage*
*Service: `backend/app/services/scoring/structured_data_scorer.py`*

| # | Criteria | Research Impact |
|---|----------|-----------------|
| SD1 | Organization schema present | Entity identity for AI knowledge graphs |
| SD2 | sameAs links (multi-platform signals) | Multi-platform entity disambiguation |
| SD3 | FAQPage schema | +28% citations (Frase.io), 3.2x in AI Overviews (BrightEdge) |
| SD4 | Article/BlogPosting schema | E-E-A-T: author attribution + dates |
| SD5 | HowTo schema | Step-by-step extraction by AI |
| SD6 | BreadcrumbList schema | Site structure clarity for AI |
| SD7 | JSON-LD validation (syntax + completeness) | Must be valid and parseable |
| SD8 | Product/Offer schema | Commercial query visibility |
| SD9 | Person schema (author credentials) | E-E-A-T author identity signals |
| SD10 | ClaimReview schema | Trust signal for factual content |
| SD11 | Structured data coverage (% of pages) | Breadth of schema adoption |
| SD12 | llms.txt presence + format validation | Low-cost signal, 844K+ sites adopted |
| SD13 | llms-full.txt presence | Full content accessibility for AI tools |

#### Category 4: Authority & SEO Signals (15%) -- READY-04
*E-E-A-T markers, entity signals, and SEO fundamentals*
*Service: `backend/app/services/scoring/authority_scorer.py`*

**E-E-A-T / Entity Signals:**

| # | Criteria | Research Impact |
|---|----------|-----------------|
| A1 | Author bios with credentials | 96% of AI-cited sources have verified E-E-A-T |
| A2 | Published/modified dates visible | 3.2x citations for content <30 days old |
| A3 | Knowledge Graph presence | Entity disambiguation for AI |
| A4 | Wikidata QID linkage | 2.8x citation likelihood |
| A5 | Wikipedia page/backlinks | #1 cited source by AI engines |
| A6 | Review platform profiles (G2, Trustpilot) | 3x citation boost from review profiles |
| A7 | Brand search volume signal | Strongest predictor (r=0.334-0.466, Ahrefs study) |
| A8 | E-E-A-T composite score | r=0.81 correlation with AI citation likelihood |

**SEO Fundamentals (directly impact AI citation likelihood):**

| # | Criteria | Research Impact |
|---|----------|-----------------|
| S1 | SSL/HTTPS | Baseline trust signal |
| S2 | Canonical tags | Prevents duplicate content confusion |
| S3 | Meta title optimization | Brand identity in search + AI |
| S4 | Meta description quality | Click-through + AI snippet source |
| S5 | XML sitemap presence | Crawl efficiency for all bots |
| S6 | Open Graph tags | Social sharing + knowledge graph signals |
| S7 | Mobile friendliness | 47% higher citation likelihood |
| S8 | Internal linking score | 2.7x citation probability (content clusters) |
| S9 | Backlink profile (DR/DA) | r=0.266 ChatGPT, higher for AI Overviews |
| S10 | Referring domains diversity | 32K+ = 3.5x more cited by ChatGPT |
| S11 | Core Web Vitals (LCP) | Page speed = citation signal |
| S12 | URL structure quality | Clean URLs for citation targeting |
| S13 | Image alt text coverage | Multimodal AI accessibility |
| S14 | Broken links (404 detection) | Trust signal degradation |
| S15 | Orphan pages detection | Content accessibility for crawlers |

**Success Criteria** (what must be TRUE):
  1. Given a crawled page, the scoring services produce sub-scores for Crawlability, Content Structure, Structured Data, and Authority
  2. Each criterion returns a 0-100 score with a human-readable comment explaining what was found and why it matters
  3. SSR detection works by rendering the page with and without JavaScript and comparing content difference
  4. AI bot access is checked per-bot (GPTBot, ClaudeBot, PerplexityBot, OAI-SearchBot, Claude-SearchBot) via robots.txt parsing
  5. Schema.org types are detected, classified by tier (Foundation/Content/Supplementary), and validated for completeness per type
  6. An Optimization Score (0-100) is computed using the weighted formula and displayed alongside the existing Visibility Score
  7. User sees a page-level breakdown with per-category scores and can drill down to see which specific criteria passed/failed and why
**Plans**: 5 plans

Plans:
- [ ] 06-01-PLAN.md -- Scoring pipeline foundation: PageScore/CriterionResult models, migration 006, SCORING Celery stage, BaseScorer interface, ScoringOrchestrator, multi-page crawl (READY-05, READY-06)
- [ ] 06-02-PLAN.md -- CrawlabilityScorer: 12 criteria for AI bot access, SSR detection, TTFB, status codes, resource blockage (READY-01)
- [ ] 06-03-PLAN.md -- ContentStructureScorer: 13 criteria for headings, answer-first, paragraphs, data density, FAQ, readability, citations, freshness, statistics, quotes, entities, sentence variety (READY-02)
- [ ] 06-04-PLAN.md -- StructuredDataScorer: 13 criteria for schema.org types, tier classification, JSON-LD validation, FAQPage, llms.txt (READY-03)
- [ ] 06-05-PLAN.md -- AuthorityScorer (23 criteria: 8 E-E-A-T + 15 SEO), Optimization Score in API, frontend scoring display with category breakdown and criterion drill-down (READY-04, READY-05, READY-06)

### Phase 7: Auto-Competitor Discovery
**Goal**: The system automatically discovers competitors from AI engine responses (who AI mentions instead of you), crawls their sites, and compares their technical setup against the user's site
**Depends on**: Phase 6 (needs page-level scoring to compare sites)
**Requirements**: COMP-01, COMP-02, COMP-03, COMP-04, COMP-05, COMP-06, COMP-07

**How it works**: Instead of asking users to manually enter competitors, the system extracts all brand/entity names mentioned in AI responses using NER (Named Entity Recognition) and pattern matching. These are ranked by mention frequency to identify the user's real AI competitors -- the brands AI recommends instead of you. Top competitors are then crawled and scored using the same Phase 6 pipeline.

**Research basis**: The Ahrefs 75K-brand study shows all three major AI platforms mention largely the same brands (r=0.779 overlap). If you're invisible in one engine, you're likely invisible in all. Auto-discovery reveals the competitive landscape as AI actually sees it.

**Success Criteria** (what must be TRUE):
  1. The system extracts all brand/entity names from AI engine responses using NER and pattern matching
  2. Discovered entities are ranked by mention frequency across all queries and engines, with share-of-voice percentages
  3. User sees a competitor leaderboard showing which brands AI mentions most for their industry queries
  4. Top 3-5 competitors (by mention frequency) are auto-crawled using the same crawl + scoring pipeline as the user's site
  5. User sees a comparison: their scores vs competitor scores per category (crawlability, content structure, schema, authority)
  6. User can add, edit, or remove custom queries alongside auto-generated ones before or after an audit runs
  7. For AI responses that cite sources (especially Perplexity), the system extracts and displays which URLs/sources each engine references
**Plans**: 4 plans

Plans:
- [ ] 07-01-PLAN.md -- Competitor/CompetitorAudit models, migration 007, EntityExtractorService (spaCy NER + citation extraction + SOV), Perplexity citations capture, DISCOVERING_COMPETITORS pipeline stage (COMP-01, COMP-02, COMP-07)
- [ ] 07-02-PLAN.md -- CompetitorService (URL resolution + crawl + score pipeline), competitor API endpoints (leaderboard, crawl trigger, detail), wire competitor crawling into audit pipeline (COMP-03, COMP-04)
- [ ] 07-03-PLAN.md -- Custom query CRUD API endpoints (add/edit/remove), QueryEditor frontend component with inline editing (COMP-06)
- [ ] 07-04-PLAN.md -- Competitors page, CompetitorLeaderboard + CompetitorComparison + SourceCitations frontend components, sidebar nav, audit page integration (COMP-05, COMP-07)

### Phase 8: Actionable Recommendations
**Goal**: The system generates page-specific, evidence-based recommendations by comparing user site scores against competitor scores and research-backed best practices, with each recommendation showing the evidence, the gap, and the estimated impact
**Depends on**: Phase 6 + Phase 7 (needs page-level scores AND competitor comparison data)
**Requirements**: REC-01, REC-02, REC-03, REC-04, REC-05

**How it works**: For each page, the system compares the user's per-criteria scores against (a) competitor scores for the same criteria, and (b) research-backed benchmarks. Gaps are identified and converted into specific, actionable recommendations. Each recommendation includes evidence from the research (e.g., "FAQPage schema gives 3.2x higher citation rate -- your competitors have it, you don't").

**Research basis for impact estimates**:
- Schema markup: 2.3-2.5x more likely in AI Overviews (BrightEdge)
- FAQPage schema: +28% AI citations (Frase.io), 3.2x citation rate (BrightEdge)
- Answer-first format: +40% citations (Princeton GEO paper)
- Statistics in content: +40% visibility boost (Princeton GEO paper)
- Quotations from authorities: +15-25% boost (Princeton GEO paper)
- Content freshness (<30 days): 3.2x more citations
- Data tables: 4.1x more AI citations (Surfer SEO)
- Content clusters with bi-directional linking: 2.7x citation probability

**Success Criteria** (what must be TRUE):
  1. The system generates page-specific recommendations by comparing user scores against competitor scores and research-backed best practices
  2. Each recommendation includes: the research-backed impact data, the specific competitor comparison, and the exact gap identified
  3. Recommendations are prioritized by estimated impact: High (>25% citation improvement), Medium (10-25%), Low (<10%) based on research data
  4. The system classifies sentiment of AI mentions (positive, negative, neutral) and surfaces sentiment patterns per engine
  5. Content gaps are identified: topics where competitors are mentioned but the user is not, linked to specific pages the user could create or improve
**Plans**: 4 plans

Plans:
- [x] 08-01-PLAN.md -- Recommendation engine + sentiment service: AuditRecommendation/MentionSentiment models, migration 008, RecommendationEngine gap analysis, SentimentService LLM classification, RECOMMENDING Celery stage (REC-01, REC-02, REC-03, REC-04)
- [x] 08-02-PLAN.md -- Content gaps + API + export: content gap identification with mini briefs, recommendation CRUD endpoints, sentiment summary API, Markdown fix plan export (REC-01, REC-02, REC-03, REC-04, REC-05)
- [x] 08-03-PLAN.md -- Frontend recommendations experience: RecommendationCard (two-tier), RecommendationProgress, SentimentBreakdown, ContentGapCard components, recommendations page with tabs/filters/export, sidebar nav, audit page preview (REC-01, REC-02, REC-03, REC-04, REC-05)
- [x] 08-04-PLAN.md -- Gap closure: Wire identify_content_gaps() and save_content_gaps() into RECOMMENDING pipeline stage (REC-05)

### Phase 9: Dashboard & Reporting
**Goal**: Users see a single-screen dashboard with their combined GEO Score (Visibility + Optimization), competitive position, top issues, and can export complete reports and track changes over time
**Depends on**: Phase 8 (needs recommendations and competitor data for complete dashboard)
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04

**Combined GEO Score**: The dashboard presents two primary scores:
- **Visibility Score** (0-100): From the AI mention-based analysis (phases 4-5)
- **Optimization Score** (0-100): From the page-level criteria scoring (phase 6)
- **Combined GEO Score**: 50/50 weighted blend displayed as the headline metric

**Success Criteria** (what must be TRUE):
  1. Dashboard shows a single-screen overview: combined GEO Score, per-engine visibility breakdown, top 5 issues to fix, competitive position summary
  2. Competitive position map shows user vs discovered competitors across key metrics (visibility score, optimization score, share of voice)
  3. User can export a complete audit report as PDF or CSV including: scores, per-criteria breakdowns, mentions with quotes, gaps identified, recommendations with evidence, and competitor comparison
  4. Audit history is stored so users can see how their scores and mention patterns change across re-audits over time (trend charts)
**Plans**: 3 plans

Plans:
- [ ] 09-01-PLAN.md -- Backend: DashboardService aggregation, dashboard API (overview, history, PDF/CSV export), Pydantic schemas, Jinja2 PDF template, WeasyPrint dependency (DASH-01, DASH-02, DASH-03, DASH-04)
- [ ] 09-02-PLAN.md -- Frontend: Dashboard page rewrite with DashboardHero scores, CompetitorRadar chart, ExportActions, per-engine breakdown, top issues, audit selector (DASH-01, DASH-02, DASH-03)
- [ ] 09-03-PLAN.md -- Frontend: TrendChart line chart for audit history, chartjs-adapter-date-fns install, dashboard history integration (DASH-04)

### Phase 10: Scale & Agency
**Goal**: Agency users can manage multiple brands under one account with separate audit histories and a cross-brand comparison dashboard
**Depends on**: Phase 9 (needs full dashboard and reporting capabilities)
**Requirements**: SCALE-01, SCALE-02

**Success Criteria** (what must be TRUE):
  1. Agency users can create and manage multiple brands under one account, each with its own URL, audit history, and score tracking
  2. Multi-brand view shows a summary dashboard comparing GEO scores, visibility scores, optimization scores, and top issues across all managed brands
**Plans**: TBD (estimate 2 plans)

Plans:
- [ ] 10-01: Brand model, multi-brand management API, per-brand audit association (SCALE-01)
- [ ] 10-02: Multi-brand dashboard with cross-brand comparison metrics (SCALE-02)

## Scoring Approach

### Built from Research, Not Legacy Code

The scoring services are built from scratch based on deep research and industry standards. The legacy `geo_data_points/` system (108 scripts, 7 modules) is **not integrated** because:
- Incompatible architecture (sync `requests` vs async `httpx`, separate DB, class-based vs service-based)
- 103 of 108 scripts are stubs returning 0
- Criteria are outdated and don't reflect current AI citation research
- Orchestrator imports are broken (paths don't match actual file structure)

Some algorithm ideas from the legacy scripts may inspire implementations (e.g., robots.txt parsing logic, heading hierarchy analysis), but all criteria are verified against current research before inclusion.

### Criteria Counts

Phase 6 implements **61 criteria** across 4 scoring categories:
- Crawlability: 12 criteria (robots.txt parsing, SSR detection, response metrics)
- Content Structure: 13 criteria (HTML analysis + NLP)
- Structured Data: 13 criteria (JSON-LD parsing + validation)
- Authority/SEO: 23 criteria (8 E-E-A-T markers + 15 SEO fundamentals)

Each criterion produces a 0-100 score with a human-readable explanation. Category scores are weighted averages of their criteria, and the Optimization Score is the weighted sum of category scores.

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8 -> 9 -> 10

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation & Safety | 3/3 | Complete | 2026-02-22 |
| 2. Site Crawl & Query Generation | 2/2 | Complete | 2026-02-22 |
| 3. AI Engine Dispatch | 2/2 | Complete | 2026-02-22 |
| 4. Mention Detection & Scoring | 2/2 | Complete | 2026-02-22 |
| 5. Audit Experience | 2/2 | Complete | 2026-02-22 |
| 6. Site AI-Readiness Scoring | 0/5 | Not started | - |
| 7. Auto-Competitor Discovery | 2/4 | Complete    | 2026-02-22 |
| 8. Actionable Recommendations | 4/4 | Complete | 2026-02-23 |
| 9. Dashboard & Reporting | 0/3 | Planned | - |
| 10. Scale & Agency | 0/2 | Not started | - |

---
*Roadmap created: 2026-02-21*
*Last updated: 2026-02-23 (Phase 9 planned: 3 plans in 2 waves)*
