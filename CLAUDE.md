# CLAUDE.md - GEO Platform MVP Guide

> **Read this file first.** It contains everything needed to understand, develop, and contribute to this project without re-exploring the codebase.
> **Then read [`docs/quickstart-your-claude.md`](docs/quickstart-your-claude.md)** for workflow rules, finding tasks, commit flow, and autopilot guidance.

## Project Overview

**GEO Platform** is a Generative Engine Optimization platform that analyzes websites against 108 data points measuring how well they're optimized for AI language models (ChatGPT, Claude, Perplexity, etc.). It scores websites 0-100 across 7 modules and generates AI-powered optimization recommendations.

**Core thesis:** As LLMs become search engines, websites need new optimization strategies beyond traditional SEO.

**Target users:** Digital agencies, SEO teams, and businesses wanting to optimize their web presence for AI-driven search.

## Current State (Honest Assessment)

**Architecture: Production-ready. Features: ~5% complete.**

| Feature | Status | Notes |
|---------|--------|-------|
| URL Analysis + Basic Scoring | Working | Visibility/Readability/Authority scores |
| Dashboard Stats | Working | Queries DB, displays results |
| GEO Data Points (5/108) | Working | GPTBot, ClaudeBot, Schema Org, Response Time, Title Tag |
| GEO Data Points (103 remaining) | Scripts exist, return 0 | Need real implementation |
| Recommendation Engine | Stub | Optimizer service exists but no LLM integration |
| Brand Signature Engine | Partial | 2 of 4 layers working (rules + pgvector similarity). Missing: statistical fingerprint + LLM deep analysis. See architecture below. |
| Stripe Payments | Stub | Endpoints exist, untested |
| Jira Integration | Stub | Endpoints exist, needs recommendations to function |
| Authentication | Disabled | JWT code ready, needs enabling |

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
| Auth | JWT (python-jose, passlib) — currently disabled |
| Task Queue | Celery + Redis |
| LLM | LiteLLM / OpenAI (recommendations + brand signature Layer 4 — not yet integrated) |
| Embeddings | OpenAI text-embedding-3-small (1536 dims) via pgvector |
| Web Scraping | Playwright, BeautifulSoup4, lxml |
| Text Analysis | textstat, NLTK |
| Database | PostgreSQL 15+ with pgvector |
| Cache | Redis 7 |
| Payments | Stripe SDK (stub) |
| Tasks | Jira API (stub) |
| Logging | Loguru |
| Containers | Docker + Docker Compose |

## Project Structure

```
geo-platform-mvp/
├── CLAUDE.md                          # This file
├── README.md                          # Public-facing project intro
├── docker-compose.yml                 # PostgreSQL + Redis + Backend + Celery + Frontend
├── .env.example                       # Environment template
├── docs/                              # All project documentation
│
├── backend/                           # FastAPI Python Backend
│   ├── app/
│   │   ├── main.py                   # App entry point + middleware stack
│   │   ├── api/                      # API routers
│   │   │   ├── analysis.py           # POST /analyze, GET /{id}
│   │   │   ├── optimization.py       # POST /generate, GET /recommendations
│   │   │   ├── brand_voice.py        # POST /check, POST /config, POST /upload
│   │   │   ├── dashboard.py          # GET /stats, GET /recent
│   │   │   ├── integrations.py       # Stripe webhooks, Jira tickets
│   │   │   └── geo_datapoints.py     # POST /run, GET /{id}, GET /summary
│   │   ├── models/                   # SQLAlchemy models
│   │   ├── services/                 # Business logic
│   │   │   ├── analyzer.py           # URL crawling + scoring
│   │   │   ├── optimizer.py          # Recommendation generation (stub)
│   │   │   ├── brand_voice.py        # Brand voice checking
│   │   │   └── jira_service.py       # Jira integration
│   │   ├── core/                     # Config, DB, security, middleware
│   │   │   ├── config.py             # Settings class (Pydantic)
│   │   │   ├── database.py           # SQLAlchemy engine + session
│   │   │   ├── security.py           # JWT auth, password hashing
│   │   │   ├── middleware.py         # 7 custom middlewares
│   │   │   └── rate_limiter.py       # Per-tier rate limiting
│   │   ├── schemas/                  # Pydantic request/response schemas
│   │   └── tasks/                    # Celery background tasks
│   ├── requirements.txt              # Python dependencies
│   └── Dockerfile
│
├── frontend/                          # Nuxt 3 Frontend
│   ├── pages/                        # Auto-routed Vue pages
│   │   ├── index.vue                 # Home/dashboard
│   │   ├── analyze.vue               # URL analysis (core feature)
│   │   ├── dashboard.vue             # Dashboard metrics
│   │   ├── optimization.vue          # Recommendations (placeholder)
│   │   ├── brand-voice.vue           # Brand voice checker
│   │   ├── settings.vue              # Settings
│   │   └── login.vue                 # Login
│   ├── components/                   # Reusable Vue components
│   ├── composables/                  # Vue composables (hooks)
│   ├── layouts/                      # Layout templates
│   ├── nuxt.config.ts                # Nuxt configuration
│   ├── package.json
│   └── Dockerfile
│
└── geo_data_points/                   # 108 GEO Measurement Scripts
    ├── measurements/                  # Individual measurement scripts
    │   ├── wi_*.py                   # Web Infrastructure (31)
    │   ├── cnt_*.py                  # Content (24)
    │   ├── bv_*.py                   # Brand Visibility (15)
    │   ├── seo_*.py                  # SEO (12)
    │   ├── ux_*.py                   # UX (8)
    │   ├── comp_*.py                 # Competitive (8)
    │   └── leg_*.py                  # Legal (5)
    ├── orchestrator/run_all.py       # Runs all measurements for a URL
    ├── utils/                        # Shared utilities (HTTP, HTML, NLP)
    ├── data_points.json              # 108 data point definitions
    └── README.md                     # Module documentation
```

## Environment Variables

### Backend (.env)
```env
SUPABASE_URL=your-project-url
SUPABASE_KEY=your-anon-key
OPENAI_API_KEY=your-openai-key
REDIS_URL=redis://localhost:6379
SECRET_KEY=your-secret-key        # openssl rand -hex 32
STRIPE_SECRET_KEY=your-stripe-key  # Optional for MVP
JIRA_BASE_URL=your-jira-url       # Optional for MVP
JIRA_API_TOKEN=your-jira-token    # Optional for MVP
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/geo_platform
```

### Frontend (.env)
```env
NUXT_PUBLIC_API_URL=http://localhost:8000
NUXT_PUBLIC_SUPABASE_URL=your-project-url
NUXT_PUBLIC_SUPABASE_KEY=your-anon-key
```

## Commands

```bash
# Docker (recommended)
docker-compose up --build           # Start all services
docker-compose logs -f backend      # View backend logs
docker-compose down                 # Stop all
docker-compose down -v              # Stop + delete data (WARNING)

# Backend (manual)
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
celery -A app.tasks.celery_app worker --loglevel=info

# Frontend (manual)
cd frontend
npm install
npm run dev

# Database
cd backend
alembic upgrade head                # Run migrations

# Testing
cd backend && pytest                # Backend tests
cd frontend && npm run test         # Frontend tests

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
User enters URL + keywords on /analyze
  -> Frontend POSTs to /api/v1/analysis/analyze
  -> Backend creates Analysis record (status=pending)
  -> Celery worker runs AnalyzerService:
     1. Crawls URL (BeautifulSoup)
     2. Calculates Visibility (keywords in H1/H2)
     3. Calculates Readability (Flesch-Kincaid)
     4. Calculates Authority (domain-based mock)
     5. Computes GEO Score = (Vis*0.4 + Read*0.3 + Auth*0.3)
  -> Frontend polls GET /api/v1/analysis/{id} every 2s
  -> Results displayed as score cards
```

## Scoring System

### Current (Simplified MVP)
- **Visibility:** keywords found in H1/H2 / total keywords * 100
- **Readability:** Flesch-Kincaid score (0-100)
- **Authority:** Mock — .edu/.gov = 85, others = random 40-70
- **GEO Score:** (Visibility * 0.4) + (Readability * 0.3) + (Authority * 0.3)

### Target (Full 108-point system)
7 modules, 108 measurements, each scoring 0-100. See `docs/GEO-DATA-POINTS.md`.

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
- **PostgreSQL + pgvector** — Single DB handles relational data AND vector embeddings. No need for separate vector DB.
- **Celery + Redis** — Background tasks for analysis (10-30s jobs). Redis also handles caching.
- **Direct LLM calls** — For recommendations, use direct OpenAI/LiteLLM calls with inline context.
- **pgvector for everything** — Brand signature uses PostgreSQL pgvector for embeddings. No external vector DB (MongoDB/Qdrant) needed.
- **4-layer brand signature** — Rules + stats + vectors + LLM. Layers 1-3 are real-time, Layer 4 is on-demand.
- **Docker Compose** — Single command to run everything. PostgreSQL, Redis, Backend, Celery, Frontend.
- **FastAPI** — Async-first, auto-generates OpenAPI docs, Pydantic validation.

## Available Subagents

Located in `.claude/awesome-claude-code-subagents/categories/`:

| Category | Relevant Agents |
|----------|----------------|
| 01-core-development | frontend-developer, backend-developer, fullstack-developer, ui-designer, api-designer |
| 02-language-specialists | python-pro, vue-expert, typescript-pro, javascript-pro, sql-pro |
| 03-infrastructure | database-administrator, deployment-engineer, security-engineer |
| 04-quality-security | code-reviewer, test-automator, accessibility-tester, performance-engineer, security-auditor, debugger, error-detective |
| 05-data-ai | ai-engineer, prompt-engineer, llm-architect |
| 06-developer-experience | documentation-engineer, refactoring-specialist, dx-optimizer |
| 07-specialized-domains | seo-specialist |

Also available as built-in Task subagent_types: frontend-developer, ui-ux-designer, code-reviewer, test-automator, security-auditor, debugger, performance-engineer, python-pro, fastapi-pro, etc.

## Agent-Invented Tasks

While working, if an agent discovers a useful improvement, they **should add it to `docs/BACKLOG.md`** under "Agent-Suggested Tasks". These tasks:

- Must be labeled `[Agent Suggested]` in the title
- Should include a brief rationale
- Are lower priority than user-requested tasks unless promoted
- Can be implemented if the agent has spare capacity during their current task
