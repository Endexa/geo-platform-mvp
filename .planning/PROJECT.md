# GEO Platform — AI Brand Visibility Auditor

## What This Is

A web application that audits how visible a brand is across AI engines (ChatGPT, Claude, Perplexity). Users enter a URL, the app crawls the site for optimization signals AND queries real AI engines to see if/how the brand appears in answers. Returns a visibility score, actual AI mentions with quotes, and a gap analysis showing what competitors get cited for that you don't.

Target customers: marketing agencies managing multiple client brands (primary) and in-house marketing teams tracking their own brand.

## Core Value

Show brands exactly how AI engines see them — with real quotes from real AI responses, not just theoretical scores.

## Requirements

### Validated

Existing codebase capabilities being repurposed:

- ✓ FastAPI backend with 4-layer architecture (middleware → routers → services → models) — existing
- ✓ Nuxt 3 SPA frontend with Tailwind CSS — existing
- ✓ PostgreSQL + pgvector database with SQLAlchemy ORM — existing
- ✓ Docker Compose multi-service setup (postgres, redis, backend, frontend) — existing
- ✓ URL crawling and basic content extraction (BeautifulSoup, Playwright available) — existing
- ✓ Basic scoring system (visibility, readability, authority) — existing, needs rethinking
- ✓ Middleware stack (security headers, rate limiting, CORS, request logging) — existing
- ✓ JWT authentication scaffolding — existing, disabled

### Active

- [ ] User enters URL and gets a complete AI brand visibility audit
- [ ] App crawls the site and checks AI-readiness signals (structured data, authority markers, content quality)
- [ ] App queries AI engines (ChatGPT, Claude, Perplexity) with auto-generated industry-relevant questions
- [ ] User can customize/add their own monitoring queries
- [ ] Results show a visibility score (0-100) with breakdown
- [ ] Results show actual AI mentions — which engines mention the brand, with real quotes
- [ ] Results show gap analysis — what competitors get mentioned for that the user doesn't
- [ ] MVP is one-time audit (user triggers manually)
- [ ] Monitoring/scheduled re-checks as paid upgrade path
- [ ] Repurpose Brand Voice engine for content analysis where applicable
- [ ] Repurpose recommendation system for actionable improvement suggestions

### Out of Scope

- Real-time continuous monitoring — MVP is audit-only, monitoring is v2 paid feature
- Mobile app — web-first
- Custom API for agency white-labeling — defer to post-MVP
- Direct content editing/rewriting — focus is on auditing and recommendations, not content generation
- Jira integration — remove, not relevant to new direction

## Context

**Existing codebase:** ~5% feature-complete against the original 108-data-point scoring spec. The original direction (score websites against 108 technical criteria) was too inward-focused — it checked the site but never checked what AI engines actually say. The redesign pivots to checking real AI engine responses.

**What stays:**
- FastAPI + Nuxt 3 + PostgreSQL stack (proven, well-structured)
- Docker Compose deployment model
- Middleware stack (security, rate limiting, logging)
- URL crawling infrastructure (BeautifulSoup, Playwright)
- pgvector for embeddings (useful for semantic comparison of AI responses)

**What changes:**
- Core analysis loop: instead of 108 data points about the page, query AI engines and analyze responses
- Scoring system: based on actual brand presence in AI answers, not just technical site signals
- Dashboard: brand visibility trends, not just page scores
- Brand Voice module: pivot from "check content tone" to "analyze how AI describes your brand"
- Optimization module: pivot from generic recommendations to "here's why AI engines don't mention you and what to fix"

**What gets removed:**
- 108-point data scoring system (geo_data_points/ directory) — replace with AI query system
- Jira integration — not relevant
- Stripe stays but reframed for monitoring upgrade path

## Constraints

- **Tech stack**: Keep FastAPI + Nuxt 3 + PostgreSQL. No stack migration.
- **AI API costs**: Querying multiple AI engines per audit has real cost. Need to design for cost efficiency (caching, smart query generation, batch where possible).
- **AI API access**: Need API access to ChatGPT, Claude, and Perplexity. Rate limits and terms of service apply.
- **Brownfield**: Must work within existing repo structure. Refactor, don't rewrite from zero.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Pivot from site-scoring to AI-presence auditing | Original 108-point system scored the site but never checked what AI actually says — that's the real value | — Pending |
| Keep existing stack (FastAPI + Nuxt + PostgreSQL) | Stack is sound, problem was product direction not technology | — Pending |
| MVP as one-time audit, monitoring as upgrade | Reduces complexity for v1, creates natural upsell | — Pending |
| Auto-generate queries from URL + allow customization | Instant value on first use while being customizable for power users | — Pending |
| Target agencies + in-house teams, agencies primary | Agencies manage multiple brands = higher contract value, natural expansion | — Pending |

---
*Last updated: 2026-02-21 after initialization*
