# Requirements: Endexa GEO Platform v2

**Defined:** 2025-02-25
**Core Value:** A user enters a URL, gets a real, trustworthy score with actionable recommendations they can immediately act on.

## v2 Requirements

### Scoring Pipeline

- [x] **SCORE-01**: All 61 scoring criteria across 4 categories produce real measurements from crawled page data
- [x] **SCORE-02**: Each criterion uses three-state system: measured, not-applicable, or error — never fabricated
- [x] **SCORE-03**: Optimization Score aggregates via weakest-link formula (0.6*mean + 0.4*min across pages)
- [x] **SCORE-04**: Dual scores displayed: Visibility Score (AI mention-based) + Optimization Score (page-level criteria)
- [x] **SCORE-05**: Crawlability category (C1-C12) produces accurate measurements including AI bot access, SSR detection, TTFB
- [x] **SCORE-06**: Content Structure category (CS1-CS13) measures headings, lists, word count, readability, citations
- [x] **SCORE-07**: Structured Data category (SD1-SD13) detects JSON-LD, FAQPage, HowTo, schema types, llms.txt
- [x] **SCORE-08**: Authority category (A1-A8, S1-S15) evaluates E-E-A-T signals and SEO fundamentals
- [x] **SCORE-09**: Dead code removed — legacy `geo_data_points/` directory deleted, only `scoring/` services used
- [x] **SCORE-10**: Scoring pipeline has integration tests verifying end-to-end accuracy against known test sites

### Recommendations Engine

- [x] **REC-01**: Deterministic gap analysis generates priority-ordered recommendations from scoring results
- [x] **REC-02**: Each recommendation includes impact estimate (estimated score improvement if fixed)
- [x] **REC-03**: Recommendations are industry-aware — vertical classification (e-commerce, SaaS, local, media) affects advice relevance
- [x] **REC-04**: Recommendations grouped by category (Crawlability, Content, Schema, Authority) with severity levels
- [x] **REC-05**: Each recommendation has a clear action description users can understand and act on

### Competitor Benchmarking

- [x] **COMP-01**: Auto-discover competitor brands from AI engine responses via NER extraction
- [x] **COMP-02**: User can view side-by-side score comparison (their site vs discovered competitors)
- [x] **COMP-03**: Share of voice tracking: percentage of AI mentions per brand across engines over time
- [x] **COMP-04**: Competitor data persists across audits to show trends

### AI Visibility

- [x] **VIS-01**: AI Visibility Score derived from real LLM queries across active engines (not fabricated)
- [x] **VIS-02**: Statistical sampling: multiple queries per engine for meaningful measurement with confidence indicators
- [x] **VIS-03**: Per-engine breakdown showing visibility on ChatGPT, Claude, Perplexity, Gemini separately
- [x] **VIS-04**: Graceful degradation: engines without API keys are skipped, score adjusts to available engines

### Reports & Exports

- [x] **RPT-01**: User can download PDF audit report with scores, recommendations, and charts
- [x] **RPT-02**: User can download HTML version of audit report
- [x] **RPT-03**: User can export recommendations as Jira-compatible CSV with customizable fields (grouping, priority, epic link)
- [x] **RPT-04**: Report includes executive summary, per-category breakdown, and top recommendations

### Chat Assistant

- [x] **CHAT-01**: User can ask questions about their audit results via chat interface
- [x] **CHAT-02**: Chat responses are grounded in the user's actual audit data (scores, recommendations, page details)
- [x] **CHAT-03**: Chat streams responses via SSE for real-time feel
- [x] **CHAT-04**: Chat handles follow-up questions with conversation context

### Code Analysis

- [ ] **CODE-01**: Endexa generates analysis prompts users can run on their codebase with their AI tools (Claude, Copilot, etc.)
- [ ] **CODE-02**: User can upload AI tool output back to Endexa for deeper analysis
- [ ] **CODE-03**: Endexa produces additional recommendations based on code analysis output
- [ ] **CODE-04**: Prompts are useful but not self-revealing (users still need Endexa for interpretation)

### Payments & Freemium

- [x] **PAY-01**: Stripe Checkout Sessions for subscription purchase flow
- [x] **PAY-02**: Stripe webhook handling for subscription lifecycle (created, updated, cancelled, payment failed)
- [x] **PAY-03**: Free tier: partial audit (crawlability category + overall score + top 3 recommendations)
- [x] **PAY-04**: Paid tier: full audit across all categories + all recommendations + exports + chat + code analysis
- [x] **PAY-05**: Feature gating enforced via FastAPI dependencies checking subscription tier

### Dashboard

- [x] **DASH-01**: Real metrics dashboard showing audit history with actual data
- [x] **DASH-02**: Score trend charts showing how scores evolve across audits over time
- [x] **DASH-03**: Per-engine AI visibility breakdown (ChatGPT, Claude, Perplexity, Gemini)
- [x] **DASH-04**: Per-category breakdown (Crawlability, Content, Schema, Authority)
- [x] **DASH-05**: Multi-site management: agencies can manage multiple client sites from one account

### Frontend Polish

- [x] **UI-01**: Production-ready UI following design system (Data-Dense Dashboard style)
- [x] **UI-02**: Audit results page shows dual scores, category breakdowns, and recommendations
- [x] **UI-03**: Responsive layout works on desktop and tablet
- [x] **UI-04**: Loading states, error states, and empty states handled throughout

## v2 Deferred (v3)

### Brand Signature
- **BRAND-01**: Statistical fingerprint analysis of brand voice
- **BRAND-02**: LLM deep analysis layer for content checking

### Advanced Features
- **ADV-01**: White-label reports for enterprise agencies
- **ADV-02**: OAuth/social login (Google, GitHub)
- **ADV-03**: Real-time monitoring and alerting (score change notifications)
- **ADV-04**: Mobile-native app
- **ADV-05**: Usage-based billing / per-audit credits on top of subscription
- **ADV-06**: Direct Jira API integration (beyond CSV export)
- **ADV-07**: IDE/VS Code plugin for inline code analysis

## Out of Scope

| Feature | Reason |
|---------|--------|
| Brand Signature Engine | Pgvector/embeddings complexity; deferred to v3 |
| Real-time monitoring | Audit-first product; monitoring is a different use case |
| Mobile app | Web responsive is sufficient for dashboard |
| White-label reports | Enterprise feature; build after proving core product |
| OAuth login | Email/password sufficient; adds complexity |
| Direct Jira API | CSV export covers 90% of use cases; API integration is complex |
| VS Code plugin | Web-first; code analysis via prompt generation covers this |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SCORE-01 | Phase 1: Scoring Foundation | Complete |
| SCORE-02 | Phase 1: Scoring Foundation | Complete |
| SCORE-03 | Phase 1: Scoring Foundation | Complete |
| SCORE-04 | Phase 1: Scoring Foundation | Complete |
| SCORE-05 | Phase 1: Scoring Foundation | Complete |
| SCORE-06 | Phase 1: Scoring Foundation | Complete |
| SCORE-07 | Phase 1: Scoring Foundation | Complete |
| SCORE-08 | Phase 1: Scoring Foundation | Complete |
| SCORE-09 | Phase 1: Scoring Foundation | Complete |
| SCORE-10 | Phase 1: Scoring Foundation | Complete |
| REC-01 | Phase 2: Recommendations + Competitor Benchmarking | Complete |
| REC-02 | Phase 2: Recommendations + Competitor Benchmarking | Complete |
| REC-03 | Phase 2: Recommendations + Competitor Benchmarking | Complete |
| REC-04 | Phase 2: Recommendations + Competitor Benchmarking | Complete |
| REC-05 | Phase 2: Recommendations + Competitor Benchmarking | Complete |
| COMP-01 | Phase 2: Recommendations + Competitor Benchmarking | Complete |
| COMP-02 | Phase 2: Recommendations + Competitor Benchmarking | Complete |
| COMP-03 | Phase 2: Recommendations + Competitor Benchmarking | Complete |
| COMP-04 | Phase 2: Recommendations + Competitor Benchmarking | Complete |
| VIS-01 | Phase 3: AI Visibility Hardening | Complete |
| VIS-02 | Phase 3: AI Visibility Hardening | Complete |
| VIS-03 | Phase 3: AI Visibility Hardening | Complete |
| VIS-04 | Phase 3: AI Visibility Hardening | Complete |
| PAY-01 | Phase 4: Payments + Freemium Gating | Complete |
| PAY-02 | Phase 4: Payments + Freemium Gating | Complete |
| PAY-03 | Phase 4: Payments + Freemium Gating | Complete |
| PAY-04 | Phase 4: Payments + Freemium Gating | Complete |
| PAY-05 | Phase 4: Payments + Freemium Gating | Complete |
| RPT-01 | Phase 5: Reports + Exports | Complete |
| RPT-02 | Phase 5: Reports + Exports | Complete |
| RPT-03 | Phase 5: Reports + Exports | Complete |
| RPT-04 | Phase 5: Reports + Exports | Complete |
| CHAT-01 | Phase 6: Chat Assistant | Complete |
| CHAT-02 | Phase 6: Chat Assistant | Complete |
| CHAT-03 | Phase 6: Chat Assistant | Complete |
| CHAT-04 | Phase 6: Chat Assistant | Complete |
| DASH-01 | Phase 7: Dashboard + Frontend Polish | Complete |
| DASH-02 | Phase 7: Dashboard + Frontend Polish | Complete |
| DASH-03 | Phase 7: Dashboard + Frontend Polish | Complete |
| DASH-04 | Phase 7: Dashboard + Frontend Polish | Complete |
| DASH-05 | Phase 7: Dashboard + Frontend Polish | Complete |
| UI-01 | Phase 7: Dashboard + Frontend Polish | Complete |
| UI-02 | Phase 7: Dashboard + Frontend Polish | Complete |
| UI-03 | Phase 7: Dashboard + Frontend Polish | Complete |
| UI-04 | Phase 7: Dashboard + Frontend Polish | Complete |
| CODE-01 | Phase 8: Code Analysis | Pending |
| CODE-02 | Phase 8: Code Analysis | Pending |
| CODE-03 | Phase 8: Code Analysis | Pending |
| CODE-04 | Phase 8: Code Analysis | Pending |

**Coverage:**
- v2 requirements: 49 total
- Mapped to phases: 49
- Unmapped: 0

---
*Requirements defined: 2025-02-25*
*Last updated: 2026-02-25 after roadmap creation -- all 49 requirements mapped to phases*
