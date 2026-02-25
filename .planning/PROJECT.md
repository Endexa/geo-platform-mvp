# Endexa GEO Platform — v2 Rebuild

## What This Is

Endexa is a Generative Engine Optimization (GEO) + SEO platform that audits websites for AI-readiness and provides actionable recommendations to improve visibility in AI-powered search engines (ChatGPT, Claude, Perplexity, Gemini). It combines traditional SEO fundamentals with next-gen AI optimization — scoring, recommendations, competitor benchmarking, code-level analysis, and Jira-ready export — in a freemium SaaS model targeting agencies, in-house SEO teams, and solo consultants.

## Core Value

A user enters a URL, gets a real, trustworthy score with actionable recommendations they can immediately act on — from fixing a robots.txt to adding JSON-LD schema to restructuring content for AI citations.

## Requirements

### Validated

Existing working infrastructure (keep as-is):

- ✓ JWT authentication (register/login/me) — Phase 1
- ✓ Celery + Redis task queue with audit pipeline — Phase 1
- ✓ AI cache (Redis, SHA-256, 24h TTL, fail-open) — Phase 1
- ✓ Outbound rate limiter (per-provider semaphore + token bucket) — Phase 1
- ✓ Cost tracking ($1.00/audit budget cap, per-call ledger) — Phase 1
- ✓ LiteLLM dispatch to 4 engines (OpenAI, Anthropic, Perplexity, Gemini) — Phase 3
- ✓ Mention detection from AI responses (NER-based) — Phase 4
- ✓ 61-criteria scoring framework (4 categories, research-backed weights) — Phase 6
- ✓ Alembic migrations — existing
- ✓ Supabase PostgreSQL + pgvector — existing

### Active

- [ ] Real scoring system that produces meaningful, accurate scores (not zeros)
- [ ] Working data point pipeline (all criteria produce real measurements)
- [ ] AI Visibility score from real LLM queries (not fabricated)
- [ ] Actionable recommendations engine with priority ordering
- [ ] Auto-competitor discovery from AI responses
- [ ] Competitor benchmarking and comparison
- [ ] PDF/HTML audit report export
- [ ] Jira CSV export (customizable: grouping, priority, fields, epic link)
- [ ] Code analysis flow: Endexa generates prompts -> user runs on repo -> uploads output -> deeper recommendations
- [ ] URL-only audit (basic) AND code-analysis audit (deep) as two tiers
- [ ] Chat assistant for audit results (ask questions, drill into issues)
- [ ] Freemium model: free partial audit (crawlability), paid full audit + recommendations
- [ ] Stripe payment integration (working checkout, subscriptions)
- [ ] Dashboard with real metrics, trend charts, history
- [ ] Polished frontend (production-ready UI, not prototype)
- [ ] Multi-site management for agencies

### Out of Scope

- Brand Signature Engine (deferred to v3 — pgvector/embeddings complexity)
- IDE/VS Code plugin integration (deferred — web-first)
- Real-time monitoring/alerting (deferred — audit-first, monitoring later)
- Mobile app (web responsive is sufficient)
- White-label reports (v3 feature for enterprise)
- OAuth/social login (email/password sufficient for v2)

## Context

### Current State (from audit)

- **Product grade**: 15/100 — only 5/108 data points work, scoring broken, AI visibility fabricated
- **Architecture grade**: 70/100 — solid FastAPI/Celery/Redis/Supabase foundation
- **Opportunity**: 90/100 — GEO tools market growing fast, no dominant affordable player

### What Works (Keep)

- Authentication system (JWT, register/login)
- Celery task queue + Redis broker
- AI cache service (Redis-based)
- Outbound rate limiter
- Cost tracking service
- LiteLLM multi-engine dispatch (OpenAI, Anthropic, Perplexity, Gemini)
- Mention detection (NER-based brand extraction)
- 61-criteria scoring framework structure (categories, weights)
- Database schema and migrations
- Frontend Nuxt 3 + Tailwind foundation

### What's Broken (Rebuild)

- 103/108 data point measurement scripts return hardcoded 0
- Scoring aggregation produces meaningless results (garbage in, garbage out)
- AI Visibility score is mock random numbers
- Recommendations engine is a stub
- Dashboard shows fake data
- Stripe integration is untested stub
- Jira integration is stub

### Market Context

- **Profound**: $35M Series B, 500+ customers, enterprise-focused ($$$)
- **Otterly.AI**: SMB-focused, basic monitoring
- **AthenaHQ**: Tech teams, ChatGPT-focused
- **Gap**: No affordable tool combining SEO + GEO with actionable recommendations + code analysis

### Competitive Differentiators

1. **Actionable recommendations** — not just scores, but exact fixes with priority
2. **SEO + GEO combined** — traditional SEO fundamentals + AI optimization in one tool
3. **Affordable** — freemium for SMBs/freelancers vs enterprise-only competitors
4. **Code analysis flow** — generate prompts for user's AI tools, ingest output for deeper analysis
5. **Jira integration** — export recommendations directly as user stories

## Constraints

- **Tech stack**: Keep FastAPI + Nuxt 3 + Supabase + Redis + Celery (proven, working)
- **AI costs**: Must stay within budget caps per audit ($1.00 default, configurable)
- **API keys**: Support multiple AI providers, gracefully skip missing keys
- **Python**: 3.11+ (CI uses 3.11)
- **Database**: Supabase PostgreSQL 17 + pgvector (remote hosted)
- **No rush**: Quality over speed — do it right

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Keep architecture, rebuild features | Architecture is 70/100, features are 15/100. Foundation is solid. | -- Pending |
| Freemium: free partial audit (crawlability) | Low barrier to entry, upsell on full audit + recommendations | -- Pending |
| SEO + GEO combined tool | Market gap — competitors do GEO only or SEO only | -- Pending |
| Code analysis via prompt generation | Users run prompts on their own repos, upload output. Avoids repo access complexity. | -- Pending |
| Jira CSV export over direct API | Simpler, works with any project management tool. Customizable fields. | -- Pending |
| No brand signature in v2 | Pgvector/embeddings complexity deferred. Focus on core audit + recommendations. | -- Pending |

---
*Last updated: 2025-02-25 after v2 project initialization*
