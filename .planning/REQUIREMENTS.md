# Requirements: GEO Platform -- AI Brand Visibility Auditor

**Defined:** 2026-02-21
**Last updated:** 2026-02-22 (roadmap rework: phases 6-10 redesigned from research; SEO+GEO combined; scoring built from scratch)
**Core Value:** Show brands exactly how AI engines see them -- with real quotes from real AI responses, not just theoretical scores. Then score their pages against research-backed SEO+GEO criteria and tell them exactly what to fix and why.
**Scoring Approach:** 53 criteria across 4 categories (Crawlability, Content Structure, Structured Data, Authority/SEO), all built from scratch based on research (Princeton GEO paper, Ahrefs 75K study, Surfer SEO 46M analysis, BrightEdge data) and industry standards. Legacy `geo_data_points/` system not used.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Foundation

- [x] **FOUND-01**: User authentication with JWT (enable existing scaffolding)
- [x] **FOUND-02**: Per-audit cost tracking with budget caps to prevent API cost explosion
- [x] **FOUND-03**: Redis caching for AI engine responses (24h TTL)
- [x] **FOUND-04**: Outbound rate limiting per AI engine API

### Core Audit

- [x] **AUDIT-01**: User can enter a URL and trigger a complete AI brand visibility audit
- [x] **AUDIT-02**: App crawls the site and extracts AI-readiness signals (schema.org, robots.txt AI directives, structured data, content structure)
- [x] **AUDIT-03**: App auto-generates industry-relevant queries from crawled site content
- [x] **AUDIT-04**: App queries ChatGPT, Claude, and Perplexity APIs with generated queries
- [x] **AUDIT-05**: App detects brand mentions in AI responses with verbatim quotes
- [x] **AUDIT-06**: User sees a visibility score (0-100) with per-engine breakdown
- [x] **AUDIT-07**: User can drill down into each query to see the full AI response with mentions highlighted

### Site AI-Readiness Scoring

- [x] **READY-01**: App scores crawlability of each page (SSR detection: render with and without JS, compare content; AI bot access via robots.txt directives for GPTBot, ClaudeBot, PerplexityBot, OAI-SearchBot, Claude-SearchBot)
- [x] **READY-02**: App scores content structure of each page (answer-first format detection, heading hierarchy quality H1>H2>H3, paragraph length analysis, data density -- tables/lists/statistics, FAQ section presence)
- [x] **READY-03**: App scores structured data quality (schema.org types present and their tier -- Foundation/Content/Supplementary, JSON-LD validation, completeness checks per schema type, FAQPage presence gets bonus weight)
- [x] **READY-04**: App scores authority and SEO signals (E-E-A-T markers: author bios, dates, citations to sources; llms.txt presence and format validation; llms-full.txt presence; multi-platform entity signals via sameAs links; SEO fundamentals: backlink profile, referring domains, Core Web Vitals, meta title/description, canonical tags, SSL, mobile friendliness, internal linking, URL structure)
- [x] **READY-05**: App produces an Optimization Score (0-100) using weighted formula: Crawlability 25% + Content Structure 25% + Schema 20% + Authority 15% + AI Visibility 15% -- displayed alongside the existing Visibility Score
- [x] **READY-06**: User sees a page-level breakdown of AI-readiness scores with per-factor drill-down (which pages score well, which score poorly, and why)

### Auto-Competitor Discovery

- [x] **COMP-01**: App extracts all brand/entity names from AI engine responses using NER (Named Entity Recognition) and pattern matching
- [x] **COMP-02**: App ranks discovered entities by mention frequency across all queries and engines to identify the user's real AI competitors (who AI mentions instead of you)
- [x] **COMP-03**: User sees a competitor leaderboard showing which brands AI mentions most for their industry queries, with share-of-voice percentages
- [x] **COMP-04**: App crawls top competitor sites (top 3-5 by mention frequency) using the same crawl pipeline as the user's site
- [ ] **COMP-05**: App compares competitor technical setup against user's site (their schema types vs yours, their content structure scores vs yours, their robots.txt AI directives vs yours, their llms.txt vs yours)
- [x] **COMP-06**: User can add/edit/remove custom queries alongside auto-generated ones before or after an audit runs
- [x] **COMP-07**: For AI responses that cite sources (especially Perplexity), the app extracts and displays which URLs/sources each engine references

### Actionable Recommendations

- [ ] **REC-01**: App generates page-specific recommendations by comparing user site scores against competitor scores and research-backed best practices (e.g., "Add FAQPage schema to /pricing -- competitors have it, you don't; FAQPage gives 3.2x higher citation rate")
- [ ] **REC-02**: Each recommendation includes evidence: the research-backed impact data, the specific competitor comparison, and the exact gap identified
- [ ] **REC-03**: Recommendations are prioritized by estimated impact (High/Medium/Low) based on research data (schema impact 2.3-2.5x, answer-first format +40%, statistics +40%, FAQ schema +28%)
- [ ] **REC-04**: App classifies sentiment of AI mentions (positive, negative, neutral) and surfaces sentiment patterns (e.g., "Perplexity describes you positively but ChatGPT is neutral")
- [ ] **REC-05**: App identifies content gaps: topics where competitors are mentioned but the user is not, linked to specific pages the user could create or improve

### Dashboard & Reporting

- [ ] **DASH-01**: Dashboard shows single-screen overview: combined GEO Score (Visibility + Optimization), per-engine breakdown, top issues, competitive position summary
- [ ] **DASH-02**: Competitive position map showing user vs discovered competitors across key metrics (visibility score, optimization score, share of voice)
- [ ] **DASH-03**: User can export a complete audit report as PDF or CSV including scores, mentions, gaps, recommendations, and competitor comparison
- [ ] **DASH-04**: App stores audit history so users can see how their scores and mention patterns change across re-audits over time

### Scale & Agency

- [ ] **SCALE-01**: Agency users can create and manage multiple brands under one account, each with separate audit history and tracking
- [ ] **SCALE-02**: Multi-brand view shows a summary dashboard comparing scores across all managed brands

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Monitoring

- **MONITOR-01**: System re-checks brand visibility on a schedule (daily/weekly)
- **MONITOR-02**: User receives alerts when visibility score changes significantly
- **MONITOR-03**: User receives alerts when AI engines change how they describe the brand

### Advanced Analysis

- **ADV-01**: Contextual mention analysis (recommendation vs. warning vs. comparison)
- **ADV-02**: Prompt variation testing (same intent, different phrasings)

### Brand Signature (Deferred from v1)

- **BRAND-01**: App extracts brand's self-positioning from their website (messaging, values, key claims, tone)
- **BRAND-02**: App compares brand self-image with how AI engines describe them
- **BRAND-03**: User sees mismatches between brand identity and AI perception (e.g., "You say premium, AI says budget")

### Agency Features

- **AGENCY-01**: White-label reports with client branding
- **AGENCY-02**: API access for programmatic audit triggering

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real-time continuous monitoring | High cost, high complexity. MVP is one-time audit. Monitoring is v2 paid tier. |
| Content rewriting / generation | Different product category. We recommend what to fix, not write it for them. |
| Deep traditional SEO (full keyword rankings, SERP position tracking, link building) | Ahrefs/Semrush own deep SEO. We include SEO fundamentals (backlinks, meta tags, Core Web Vitals) as scoring criteria since they directly impact AI citation likelihood, but we don't replicate full SEO suites. |
| Social media monitoring | Different domain. Brandwatch/Mention own this. |
| Browser extension | Engineering distraction. Web-first is sufficient. |
| AI chatbot for results interpretation | Dashboard should be self-explanatory. If it needs a chatbot, the UX needs work. |
| Mobile app | Web-first. Mobile later. |
| Jira integration | Not relevant to new product direction. |
| Brand signature analysis | Deferred to v2. Complexity of semantic comparison (pgvector, embeddings) is high. Focus v1 on concrete, measurable gaps (technical + content + schema) not subjective brand perception. |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| FOUND-01 | Phase 1: Foundation & Safety | Complete |
| FOUND-02 | Phase 1: Foundation & Safety | Complete |
| FOUND-03 | Phase 1: Foundation & Safety | Complete |
| FOUND-04 | Phase 1: Foundation & Safety | Complete |
| AUDIT-01 | Phase 5: Audit Experience | Complete |
| AUDIT-02 | Phase 2: Site Crawl & Query Generation | Complete |
| AUDIT-03 | Phase 2: Site Crawl & Query Generation | Complete |
| AUDIT-04 | Phase 3: AI Engine Dispatch | Complete |
| AUDIT-05 | Phase 4: Mention Detection & Scoring | Complete |
| AUDIT-06 | Phase 4: Mention Detection & Scoring | Complete |
| AUDIT-07 | Phase 5: Audit Experience | Complete |
| READY-01 | Phase 6: Site AI-Readiness Scoring | Complete |
| READY-02 | Phase 6: Site AI-Readiness Scoring | Complete |
| READY-03 | Phase 6: Site AI-Readiness Scoring | Complete |
| READY-04 | Phase 6: Site AI-Readiness Scoring | Complete |
| READY-05 | Phase 6: Site AI-Readiness Scoring | Complete |
| READY-06 | Phase 6: Site AI-Readiness Scoring | Complete |
| COMP-01 | Phase 7: Auto-Competitor Discovery | Complete |
| COMP-02 | Phase 7: Auto-Competitor Discovery | Complete |
| COMP-03 | Phase 7: Auto-Competitor Discovery | Complete |
| COMP-04 | Phase 7: Auto-Competitor Discovery | Complete |
| COMP-05 | Phase 7: Auto-Competitor Discovery | Pending |
| COMP-06 | Phase 7: Auto-Competitor Discovery | Complete |
| COMP-07 | Phase 7: Auto-Competitor Discovery | Complete |
| REC-01 | Phase 8: Actionable Recommendations | Pending |
| REC-02 | Phase 8: Actionable Recommendations | Pending |
| REC-03 | Phase 8: Actionable Recommendations | Pending |
| REC-04 | Phase 8: Actionable Recommendations | Pending |
| REC-05 | Phase 8: Actionable Recommendations | Pending |
| DASH-01 | Phase 9: Dashboard & Reporting | Pending |
| DASH-02 | Phase 9: Dashboard & Reporting | Pending |
| DASH-03 | Phase 9: Dashboard & Reporting | Pending |
| DASH-04 | Phase 9: Dashboard & Reporting | Pending |
| SCALE-01 | Phase 10: Scale & Agency | Pending |
| SCALE-02 | Phase 10: Scale & Agency | Pending |

**Coverage:**
- v1 requirements: 35 total
- Mapped to phases: 35
- Unmapped: 0

---
*Requirements defined: 2026-02-21*
*Last updated: 2026-02-22 after roadmap rework (phases 6-10 redesigned from research)*
