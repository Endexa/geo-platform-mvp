# Requirements: GEO Platform -- AI Brand Visibility Auditor

**Defined:** 2026-02-21
**Core Value:** Show brands exactly how AI engines see them -- with real quotes from real AI responses, not just theoretical scores.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Foundation

- [x] **FOUND-01**: User authentication with JWT (enable existing scaffolding)
- [x] **FOUND-02**: Per-audit cost tracking with budget caps to prevent API cost explosion
- [ ] **FOUND-03**: Redis caching for AI engine responses (24h TTL)
- [ ] **FOUND-04**: Outbound rate limiting per AI engine API

### Core Audit

- [ ] **AUDIT-01**: User can enter a URL and trigger a complete AI brand visibility audit
- [ ] **AUDIT-02**: App crawls the site and extracts AI-readiness signals (schema.org, robots.txt AI directives, structured data, content structure)
- [ ] **AUDIT-03**: App auto-generates industry-relevant queries from crawled site content
- [ ] **AUDIT-04**: App queries ChatGPT, Claude, and Perplexity APIs with generated queries
- [ ] **AUDIT-05**: App detects brand mentions in AI responses with verbatim quotes
- [ ] **AUDIT-06**: User sees a visibility score (0-100) with per-engine breakdown
- [ ] **AUDIT-07**: User can drill down into each query to see the full AI response with mentions highlighted

### Competitive Intelligence

- [ ] **COMP-01**: User can add competitor brands for comparison
- [ ] **COMP-02**: App runs the same queries for competitors and shows gap analysis (what they get mentioned for that user doesn't)
- [ ] **COMP-03**: User can add/edit/remove custom queries alongside auto-generated ones
- [ ] **COMP-04**: App tracks which sources AI engines cite in their responses (source attribution)

### Brand Signature

- [ ] **BRAND-01**: App extracts brand's self-positioning from their website (messaging, values, key claims, tone)
- [ ] **BRAND-02**: App compares brand self-image with how AI engines describe them
- [ ] **BRAND-03**: User sees mismatches between brand identity and AI perception (e.g., "You say premium, AI says budget")

### Insights & Actions

- [ ] **INSIGHT-01**: App generates actionable recommendations (what to fix and why to improve AI visibility)
- [ ] **INSIGHT-02**: Dashboard shows single-screen overview with visibility score, per-engine breakdown, top issues
- [ ] **INSIGHT-03**: App analyzes sentiment of AI mentions (positive/negative/neutral)

### Reporting & Scale

- [ ] **REPORT-01**: User can export audit results as PDF or CSV
- [ ] **REPORT-02**: App stores query history so user can see visibility trends over time
- [ ] **REPORT-03**: Agencies can manage multiple brands under one account with separate tracking

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Monitoring

- **MONITOR-01**: System re-checks brand visibility on a schedule (daily/weekly)
- **MONITOR-02**: User receives alerts when visibility score changes significantly
- **MONITOR-03**: User receives alerts when AI engines change how they describe the brand

### Advanced Analysis

- **ADV-01**: Contextual mention analysis (recommendation vs. warning vs. comparison)
- **ADV-02**: Content-level gap identification (specific content changes to improve AI visibility)
- **ADV-03**: Prompt variation testing (same intent, different phrasings)

### Agency Features

- **AGENCY-01**: White-label reports with client branding
- **AGENCY-02**: API access for programmatic audit triggering

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real-time continuous monitoring | High cost, high complexity. MVP is one-time audit. Monitoring is v2 paid tier. |
| Content rewriting / generation | Different product category. We recommend what to fix, not write it for them. |
| Traditional SEO metrics (backlinks, rankings) | Ahrefs/Semrush own this. Dilutes GEO positioning. |
| Social media monitoring | Different domain. Brandwatch/Mention own this. |
| Browser extension | Engineering distraction. Web-first is sufficient. |
| AI chatbot for results interpretation | Dashboard should be self-explanatory. If it needs a chatbot, the UX needs work. |
| Mobile app | Web-first. Mobile later. |
| Jira integration | Not relevant to new product direction. |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| FOUND-01 | Phase 1: Foundation & Safety | Complete |
| FOUND-02 | Phase 1: Foundation & Safety | Complete |
| FOUND-03 | Phase 1: Foundation & Safety | Pending |
| FOUND-04 | Phase 1: Foundation & Safety | Pending |
| AUDIT-01 | Phase 5: Audit Experience | Pending |
| AUDIT-02 | Phase 2: Site Crawl & Query Generation | Pending |
| AUDIT-03 | Phase 2: Site Crawl & Query Generation | Pending |
| AUDIT-04 | Phase 3: AI Engine Dispatch | Pending |
| AUDIT-05 | Phase 4: Mention Detection & Scoring | Pending |
| AUDIT-06 | Phase 4: Mention Detection & Scoring | Pending |
| AUDIT-07 | Phase 5: Audit Experience | Pending |
| COMP-01 | Phase 6: Competitive Intelligence | Pending |
| COMP-02 | Phase 6: Competitive Intelligence | Pending |
| COMP-03 | Phase 6: Competitive Intelligence | Pending |
| COMP-04 | Phase 6: Competitive Intelligence | Pending |
| BRAND-01 | Phase 7: Brand Signature Analysis | Pending |
| BRAND-02 | Phase 7: Brand Signature Analysis | Pending |
| BRAND-03 | Phase 7: Brand Signature Analysis | Pending |
| INSIGHT-01 | Phase 8: Insights & Dashboard | Pending |
| INSIGHT-02 | Phase 8: Insights & Dashboard | Pending |
| INSIGHT-03 | Phase 8: Insights & Dashboard | Pending |
| REPORT-01 | Phase 9: Reporting & Scale | Pending |
| REPORT-02 | Phase 9: Reporting & Scale | Pending |
| REPORT-03 | Phase 9: Reporting & Scale | Pending |

**Coverage:**
- v1 requirements: 24 total
- Mapped to phases: 24
- Unmapped: 0

---
*Requirements defined: 2026-02-21*
*Last updated: 2026-02-21 after roadmap creation*
