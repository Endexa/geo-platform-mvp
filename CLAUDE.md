# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **Read this file first.** It contains everything needed to understand, develop, and contribute to this project without re-exploring the codebase.
> **Then read [`docs/quickstart-your-claude.md`](docs/quickstart-your-claude.md)** for workflow rules, finding tasks, commit flow, and autopilot guidance.

## Project Overview

**GEO Platform** is a Generative Engine Optimization platform that analyzes websites against 61 criteria (across 5 categories) measuring how well they're optimized for AI language models (ChatGPT, Claude, Perplexity, etc.). It produces a dual score — Visibility (are LLMs mentioning you?) + Optimization (is your site technically ready to be cited?) — and generates AI-powered optimization recommendations.

**Core thesis:** As LLMs become search engines, websites need new optimization strategies beyond traditional SEO.

**Target users:** Digital agencies, SEO teams, and businesses wanting to optimize their web presence for AI-driven search.

## Current State (Honest Assessment)

**Architecture: Production-ready. Features: ~40% complete.**

| Feature | Status | Notes |
|---------|--------|-------|
| Authentication | ✅ Working | PyJWT + pwdlib/bcrypt, register/login/me, all protected endpoints enforced |
| Full Audit Pipeline | ✅ Working | 8-stage Celery pipeline: crawl → query gen → dispatch → mentions → scoring → competitors → sentiment → recommendations |
| Multi-LLM Dispatch | ✅ Working | LiteLLM routing to OpenAI/Anthropic/Perplexity/Gemini/Mistral in parallel (ThreadPoolExecutor) |
| AI Response Cache | ✅ Working | Redis SHA-256 keys, 24h TTL, fail-open |
| Cost Tracking | ✅ Working | AuditCostLedger per call, $1.00/audit budget cap, pre-query budget check |
| Outbound Rate Limiter | ✅ Working | asyncio semaphore + token bucket per provider |
| Query Generator | ✅ Working | LLM generates 10-15 queries in 5 categories (industry/brand_direct/comparison/problem/recommendation) |
| Brand Mention Detection | ✅ Working | Exact regex + RapidFuzz fuzzy fallback, context_quote extraction, brand variant generation |
| Visibility Score | ✅ Working | 40% mention_rate + 30% position + 30% prominence, per-engine breakdown |
| AI-Readiness Scoring (61 criteria) | ✅ Working | CrawlabilityScorer (C1-C12), ContentStructureScorer (CS1-CS13), StructuredDataScorer (SD1-SD13), AuthorityScorer (A1-A8 + S1-S15) |
| Scoring: External APIs | ✅ Working | Knowledge Graph, Wikidata, Wikipedia, PageSpeed Insights — graceful degradation |
| Weakest-link Aggregation | ✅ Working | score = 0.6×mean + 0.4×min per page, then across pages |
| Site Vertical Classifier | ✅ Working | Detects saas/ecommerce/local_business/media_blog/healthcare/legal/finance/generic |
| Competitor Discovery | ✅ Working | spaCy NER on LLM responses → entity dedup (RapidFuzz) → URL resolution (citation URL > domain heuristic > KG API) |
| Competitor Crawl + Scoring | ✅ Working | Top competitors crawled and scored with Phase 6 pipeline, CompetitorAudit per-category averages |
| Share-of-Voice tracking | ✅ Working | DiscoveredCompetitor.queries_mentioned_in[], linked to Brand records across audits |
| Sentiment Analysis | ✅ Working | Mistral-small via LiteLLM, JSON mode, positive/negative/neutral per mention |
| Recommendation Engine | ✅ Working | Deterministic gap analysis: criterion score vs competitor avg vs research benchmarks, priority HIGH/MEDIUM/LOW, code snippets, estimated_score_delta |
| Content Gaps | ✅ Working | Queries where competitors mentioned but brand is not → mini brief per gap |
| Markdown Fix Plan Export | ✅ Working | Structured PLAN.md format exportable per page or full site |
| Dashboard | ✅ Working | DashboardHero (score cards), CompetitorRadar (Chart.js), ExportActions, TrendChart, audit history |
| PDF/CSV Export | ✅ Working | WeasyPrint PDF, CSV via DashboardService, Jinja2 template |
| Citability Scoring | ✅ Working | Scores how citable a page is for LLMs. DB models + migration in place |
| llms.txt Generation | ✅ Working | Auto-generates llms.txt / llms-full.txt files for AI crawler discovery |
| Brand Scanning | ✅ Working | Scans LLM responses for brand presence across platforms |
| Chat Assistant | ✅ Working | SSE streaming chat via LiteLLM, ChatPanel component, chat sessions persisted |
| Code Analysis | ✅ Working | Analyze code snippets for GEO optimization patterns |
| Report Generation | ✅ Working | Full audit reports via ReportService, exportable |
| Brand Signature Engine | ⚠️ Partial | Layer 1 (rules/regex) + Layer 3 (pgvector cosine similarity) working. Layer 2 (statistical fingerprint) + Layer 4 (LLM deep analysis) not built. |
| geo_datapoints/ legacy system | ❌ Deleted | 108-script system removed. Replaced by Phase 6 scoring (61 criteria). `/geo-datapoints` endpoints return null. |
| Stripe Payments | ❌ Stub | Endpoints exist, webhook handler skeleton, no real logic |
| Jira Integration | ❌ Stub | Endpoint exists, no implementation |
| Alembic Migrations | ✅ Working | 16 versioned migrations covering all current models |

## Git & Commit Rules

- **After each completed task, create a git commit** with a simple, descriptive message.
- **Never include** "authored by Claude", "Co-Authored-By: Claude", or any AI attribution in commit messages.
- Commit messages should be short and descriptive: `"Add schema.org FAQPage measurement"`, `"Fix analysis polling timeout"`.
- Always update `docs/progression.md` when a task is completed before committing.
- Update `CLAUDE.md` if the task changes architecture, adds new patterns, or modifies how things work.

## Key Project Files

- **CLAUDE.md** (this file) - Complete project guide. Update when architecture changes.
- **docs/quickstart-your-claude.md** - Workflow guide for new sessions. How to find work, commit, test, use agents.
- **docs/BACKLOG.md** - Prioritized task breakdown with dependencies. The implementation plan.
- **docs/progression.md** - Tracks what's done, what's broken, changelog. Update after every task.
- **docs/CONNECTIONS.md** - External service map with health check commands.
- **docs/DEPLOYMENTS.md** - Deployment log. Update after every deploy.
- **docs/INCIDENTS.md** - **Check FIRST when debugging any error.** Known errors + exact fixes by category.
- **docs/ARCHITECTURE.md** - System architecture, data flow, middleware stack.
- **docs/GEO-DATA-POINTS.md** - The 108-measurement system: modules, scoring, how to add scripts.
- **docs/API-REFERENCE.md** - All API endpoints, schemas, auth requirements.
- **docs/TESTING-STRATEGY.md** - Testing tiers and scope matrix.
- **docs/SECURITY.md** - Security implementation details.
- **docs/RedwaneNextDirection.md** - 5-axis roadmap for score architecture redesign, Share of Model KPI, score delta, Brand Signature L2/L4, and new GEO modules. **Read before touching scoring or the audit pipeline.**
- **docs/GEO-DATA-POINTS-CLASSIFICATION.md** - Classification of 109 GEO data points (priority P0-P5, full implementation spec per point).
- **docs/archive/** - Historical docs. See `docs/archive/README.md` for index.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Nuxt 3 (Vue 3) + TypeScript |
| Styling | Tailwind CSS |
| UI Components | Headless UI, Heroicons, Lucide Vue |
| Charts | Chart.js + vue-chartjs |
| Backend | FastAPI (Python 3.11+) |
| ORM | SQLAlchemy + Alembic migrations |
| Validation | Pydantic v2 |
| Auth | JWT (PyJWT, pwdlib/bcrypt) — enabled on all protected endpoints |
| Task Queue | Celery + Redis |
| LLM | LiteLLM / OpenAI (recommendations + brand signature Layer 4 — not yet integrated) |
| Embeddings | OpenAI text-embedding-3-small (1536 dims) via pgvector |
| Web Scraping | Playwright, BeautifulSoup4, lxml |
| Text Analysis | textstat, NLTK |
| Database | Supabase PostgreSQL 17 + pgvector (remote) |
| Cache | Redis 7 (local Docker container) |
| Payments | Stripe SDK (stub) |
| Tasks | Jira API (stub) |
| Logging | Loguru |

## Project Structure

```
geo-platform-mvp/
├── CLAUDE.md                          # This file
├── start.sh                           # One-command dev launcher
├── docker-compose.yml                 # Redis + optional full Docker dev setup
├── docs/                              # All project documentation
│
├── backend/                           # FastAPI Python Backend
│   ├── app/
│   │   ├── main.py                   # App entry + middleware stack (9 middlewares)
│   │   ├── api/                      # 16 API routers (audit, auth, analysis, brands, brand_voice,
│   │   │                             #   chat, code_analysis, competitors, dashboard, geo_datapoints,
│   │   │                             #   integrations, optimization, payments, recommendations, reports)
│   │   ├── models/                   # 25 SQLAlchemy models
│   │   ├── services/                 # Business logic (~27 service files)
│   │   │   └── scoring/             # Scoring subsystem (critical path)
│   │   │       ├── base_scorer.py           # ABC for all scorers
│   │   │       ├── scoring_orchestrator.py  # Runs all scorers, weakest-link aggregation
│   │   │       ├── crawlability_scorer.py   # C1-C12
│   │   │       ├── content_structure_scorer.py # CS1-CS13
│   │   │       ├── structured_data_scorer.py   # SD1-SD13
│   │   │       └── authority_scorer.py      # A1-A8 + S1-S15
│   │   ├── core/                     # Config, DB, security, middleware, rate limiting
│   │   ├── schemas/                  # Pydantic request/response schemas
│   │   └── tasks/                    # Celery tasks (audit_tasks.py is the main pipeline)
│   ├── tests/                        # pytest tests (~20 test files)
│   ├── alembic/                      # 16 versioned migrations
│   └── requirements.txt
│
└── frontend/                          # Nuxt 3 Frontend (SPA mode)
    ├── pages/                        # 12 auto-routed pages (index, analyze, audit, dashboard,
    │                                 #   brands, competitors, recommendations, brand-voice,
    │                                 #   optimization, pricing, settings, login)
    ├── components/                   # ~36 Vue components + landing/ subdirectory
    ├── composables/                  # 10 composables (useAuth, useAudit, useApiFetch, etc.)
    └── nuxt.config.ts                # Modules: @nuxtjs/tailwindcss, @pinia/nuxt
```

## Environment Variables

### Backend (.env)
```env
DATABASE_URL=postgresql://postgres:PASSWORD@db.PROJECT_REF.supabase.co:5432/postgres
SUPABASE_URL=https://PROJECT_REF.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key        # openssl rand -hex 32
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
GEMINI_API_KEY=your-gemini-key
MISTRAL_API_KEY=your-mistral-key    # Used for sentiment analysis (Mistral-small via LiteLLM)
```

### Frontend (.env)
```env
NUXT_PUBLIC_API_URL=http://localhost:8000      # Note: NOT _API_BASE — see nuxt.config.ts
NUXT_PUBLIC_SUPABASE_URL=https://PROJECT_REF.supabase.co
NUXT_PUBLIC_SUPABASE_KEY=your-anon-key
NUXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_... # Optional, for payments
NUXT_PUBLIC_STRIPE_PRICE_PRO_MONTHLY=price_... # Optional, for payments
```

## Commands

```bash
# One command start (recommended)
./start.sh                          # Starts Redis, migrations, backend, Celery, frontend

# Manual start (3 terminals)
docker start geo-redis || docker run -d --name geo-redis -p 6379:6379 redis:7-alpine
cd backend && source venv/bin/activate && uvicorn app.main:app --reload --port 8000
cd backend && source venv/bin/activate && celery -A app.tasks.celery_app worker --loglevel=info -Q geo_platform,audit,analysis
cd frontend && npm run dev

# Database (Supabase — remote)
cd backend && source venv/bin/activate
alembic upgrade head                # Run migrations against Supabase

# Testing
cd backend && source venv/bin/activate && pytest                          # All backend tests
cd backend && source venv/bin/activate && pytest tests/test_analysis.py   # Single test file
cd backend && source venv/bin/activate && pytest tests/test_analysis.py -k "test_name" # Single test
cd frontend && npm run test:e2e     # E2E tests (Playwright, mocked API)
cd frontend && npm run test:e2e:ui  # E2E with interactive UI
cd frontend && npm run lint         # ESLint
cd frontend && npm run build        # Build check

# Access points
# Frontend: http://localhost:3000
# API Docs: http://localhost:8000/api/v1/docs
# Health:   http://localhost:8000/health
```

### Task Completion Checklist

Before marking any task as done:

1. Backend: `pytest` passes (if tests exist for changed code)
2. Frontend: `npm run build` passes
3. Docker: `docker-compose up --build` starts without errors
4. Update `docs/progression.md` changelog
5. Update `CLAUDE.md` if architecture changed
6. Commit with descriptive message (no AI attribution)

## Core User Journey

```
User enters URL on /analyze
  -> Frontend POSTs to /api/v1/audit/
  -> Backend creates Audit record (status=CRAWLING)
  -> Celery worker runs run_crawl_and_generate():
     1. CRAWLING          — BeautifulSoup + extruct crawl; vertical classification (spaCy)
     2. GENERATING_QUERIES — LLM generates 10-15 queries in 5 categories (GPT-4o-mini)
     3. DISPATCHING       — Queries sent to 5 AI engines in parallel (ThreadPoolExecutor)
     4. ANALYZING         — Brand mention detection (regex + RapidFuzz); Visibility Score computed
     5. SCORING           — Multi-page crawl; 4 scorers run per page; weakest-link aggregation
     6. DISCOVERING_COMPETITORS — spaCy NER on responses; URL resolution; competitor crawl+score
     7. RECOMMENDING      — Gap analysis vs competitors; sentiment analysis (Mistral)
     8. COMPLETED
  -> Frontend polls GET /api/v1/audit/{id} every 2s
  -> Results: dual-score display (Visibility + Optimization), per-engine breakdown,
     CategoryBreakdown, CriterionDrilldown, CompetitorRadar, recommendations
```

## Scoring System

### Dual-Score Architecture (Phase 6 Complete)

The audit produces two complementary scores displayed side by side in the UI:

**Score #1 — Visibility Score (0-100)**
Measures how often AI engines *actually* mention your brand when asked real industry queries.
- Source: Brand mentions detected in LLM responses (Stage 4)
- Formula: `40% mention_rate + 30% position_score + 30% prominence_score`
- Per-engine breakdown: OpenAI / Anthropic / Perplexity / Gemini / Mistral
- This is the **true GEO metric** — did the LLMs mention you or not?

**Score #2 — Optimization Score (0-100)**
Measures how technically ready the site is to *be* cited by AI engines.
- Source: 61 criteria evaluated page by page (Stage 5)
- This is a **readiness proxy**, not a direct GEO measurement

**Final weighted formula:**
```
optimization_score = (crawlability×0.25 + content_structure×0.25 + structured_data×0.20 + authority×0.15 + ai_visibility×0.15) per page
page_score = 0.6×mean(criteria) + 0.4×min(criteria)   ← weakest-link per page
final_score = 0.6×mean(pages) + 0.4×min(pages)         ← weakest-link across pages
```
The two scores (Visibility + Optimization) are stored separately. See `docs/RedwaneNextDirection.md` for the planned UI redesign to surface them as independent dimensions.

**Categories:**
| Category | Criteria | Weight | Key Signals | Implementation |
|----------|----------|--------|-------------|----------------|
| Crawlability | C1-C12 | 25% | 8 AI bot robots.txt checks, SSR detection (Playwright), TTFB, HTTP status, resource blockage | `crawlability_scorer.py` |
| Content Structure | CS1-CS13 | 25% | Headings, answer-first, paragraph length, data density, FAQ, content length, readability (textstat), citations, freshness, statistics, quotations, entity density, sentence variety | `content_structure_scorer.py` |
| Structured Data | SD1-SD13 | 20% | JSON-LD Organization/sameAs/FAQPage/Article/HowTo/Breadcrumb/Product/Person/ClaimReview, validity, coverage, llms.txt, llms-full.txt | `structured_data_scorer.py` |
| Authority | A1-A8 + S1-S15 | 15% | E-E-A-T (author bios, dates, KG API, Wikidata SPARQL, Wikipedia API, reviews, brand signal, composite), SSL, canonical, meta, sitemap, OG, mobile, internal links, backlink proxy, CWV (PageSpeed API), URL structure, alt text, broken links, orphan pages | `authority_scorer.py` |
| AI Visibility | COMP1+ | 15% | Share of Model per engine (queries_with_mentions / queries_sent); data sourced from VisibilityScore table | `som_scorer.py` (planned — see `docs/RedwaneNextDirection.md` Axe 5) |

## Brand Signature Engine (4-Layer Architecture)

The Brand Signature module checks if new content matches a brand's established voice. It uses 4 independent layers, each catching different types of brand drift:

```
Layer 1: RULES ENGINE            (instant, free)     → forbidden words, required phrases, regex
Layer 2: STATISTICAL FINGERPRINT (< 100ms, free)     → sentence length, vocabulary richness, readability, formality
Layer 3: SEMANTIC SIMILARITY     (< 500ms, ~$0.001)  → pgvector cosine similarity against brand corpus
Layer 4: LLM DEEP ANALYSIS      (2-5s, ~$0.02)      → on-demand explanations with brand examples
```

**Current status:** Layers 1 + 3 working (`backend/app/services/brand_voice.py`). Layers 2 + 4 not yet built.

**Scoring:**
- Fast mode (layers 1-3): `rules×0.2 + stats×0.3 + semantic×0.5`
- Deep mode (all 4): `rules×0.15 + stats×0.2 + semantic×0.35 + llm×0.3`

**Infrastructure:** PostgreSQL + pgvector only. No external vector DB needed.

**Key files:**
- `backend/app/services/brand_voice.py` — Core service (chunking, embedding, similarity, rules)
- `backend/app/api/brand_voice.py` — API endpoints (config, upload, rules, check)
- `backend/app/models/brand_voice.py` — DB models (BrandVoiceConfig, VoiceVector, VoiceRule)

See `docs/ARCHITECTURE.md` for the full design.

## Middleware Stack (order matters)

1. ErrorSanitizationMiddleware (outermost)
2. RequestSizeLimitMiddleware (10MB)
3. SecurityHeadersMiddleware (CSP, HSTS, X-Frame-Options)
4. RequestLoggingMiddleware + AuditLogMiddleware
5. SQLInjectionProtectionMiddleware
6. APIVersionMiddleware
7. GZipMiddleware
8. TrustedHostMiddleware (production only)
9. CORSMiddleware (innermost)

## Architecture Decisions

- **No SSR** — Nuxt 3 SPA mode. This is a dashboard app, not a content site.
- **Supabase PostgreSQL + pgvector** — Remote hosted DB. Single DB handles relational data AND vector embeddings. No local Postgres needed.
- **Celery + Redis** — Background tasks for analysis (10-30s jobs). Redis also handles caching. Redis runs locally via Docker.
- **Direct LLM calls** — For recommendations, use direct OpenAI/LiteLLM calls with inline context.
- **pgvector for everything** — Brand signature uses PostgreSQL pgvector for embeddings. No external vector DB (MongoDB/Qdrant) needed.
- **4-layer brand signature** — Rules + stats + vectors + LLM. Layers 1-3 are real-time, Layer 4 is on-demand.
- **`start.sh`** — Single command to run everything. Redis (Docker), migrations, Backend, Celery, Frontend.
- **FastAPI** — Async-first, auto-generates OpenAPI docs, Pydantic validation.

## Installed Development Tools

Three plugins are installed that change how you work. They activate automatically — read this to understand the workflow they enforce.

### 1. Superpowers (Workflow Enforcement)

Auto-activates on session start. Enforces: brainstorm → plan (save to `docs/plans/`) → TDD (failing test first) → code review. Design doc required before implementation. No production code without a failing test first.

**Location:** `~/.claude/plugins/cache/superpowers/superpowers/unknown/skills/`

### 2. GSD — Get Shit Done (Spec-Driven Development)

Slash commands for phased development with requirements tracking. Use for non-trivial features.

**Key commands:** `/gsd:new-project` (full lifecycle), `/gsd:plan-phase N`, `/gsd:execute-phase N`, `/gsd:quick` (small tasks), `/gsd:debug`

**Artifacts:** `.planning/` directory

### 3. UI/UX Pro Max (Design System)

Auto-activates on frontend work. Enforces the design system at `design-system/endexa-geo-platform/MASTER.md`.

**Design tokens:** Primary `#1E40AF`, Secondary `#3B82F6`, CTA `#F59E0B`, Background `#F8FAFC`, Text `#1E3A8A`. Typography: Fira Code (headings/data) + Fira Sans (body/UI).

**Rules:** No emoji icons (use Heroicons/Lucide SVG), no `z-[9999]`, transitions cap 300ms, `cursor-pointer` on clickables, `focus-visible:ring-2`, min 4.5:1 contrast.

**Location:** `.claude/skills/ui-ux-pro-max/`

---

## Available Subagents

Located in `.claude/awesome-claude-code-subagents/categories/` (01-core-development through 07-specialized-domains). Also available as Task subagent_types: `frontend-developer`, `backend-developer`, `code-reviewer`, `test-automator`, `security-auditor`, `debugger`, `python-pro`, `fastapi-pro`, `vue-expert`, etc.

## Agent-Invented Tasks

While working, if an agent discovers a useful improvement, they **should add it to `docs/BACKLOG.md`** under "Agent-Suggested Tasks". These tasks:

- Must be labeled `[Agent Suggested]` in the title
- Should include a brief rationale
- Are lower priority than user-requested tasks unless promoted
- Can be implemented if the agent has spare capacity during their current task
