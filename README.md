# GEO Platform MVP

A Generative Engine Optimization (GEO) platform that analyzes how well websites are optimized for AI language models (ChatGPT, Claude, Perplexity, Gemini, Mistral). Scores websites 0-100 across 61 criteria and generates optimization recommendations.

## What the Platform Does

**Core thesis:** as LLMs become search engines, websites need optimization beyond classic SEO. The platform combines **SEO + GEO** in one audit, tells you *what to fix*, and exports the fixes to your task tracker.

**Target users:** agencies, in-house SEO teams, solo consultants.

### The audit pipeline

1. **Submit** a URL (and optionally a brand, competitors and custom queries). The audit runs asynchronously in Celery (`202 Accepted`, then poll).
2. **Crawl** the site: robots.txt, sitemap, rendered HTML, JSON-LD, headers, TTFB, AI-bot access.
3. **Classify the vertical** (SaaS, e-commerce, local business, media/blog, B2B services, generic) from schema.org types and URL/HTML patterns. Recommendations that do not apply to the vertical are filtered out. When confidence is low it falls back to `generic` (no filtering).
4. **Generate queries**: an LLM builds industry-relevant questions from the crawled content. You can add, edit or delete them.
5. **Dispatch to AI engines** (ChatGPT, Claude, Perplexity, Gemini, Mistral) in parallel. Engines without an API key are skipped (no thread, no DB write). Auth and rate-limit errors remove an engine from the pool fast.
6. **Detect brand mentions**, citations and sentiment in each response and compute per-engine **share of voice**.
7. **Score the pages** against 61 criteria (below).
8. **Compare to competitors** (up to 5 auto-crawled) and surface content gaps.
9. **Generate recommendations**, prioritized, with impact estimates and action steps.
10. **Report and export**: dashboard, PDF report, CSV, Jira CSV/tickets, Markdown.

### Two scores

| Score | What it measures |
|-------|------------------|
| **Visibility Score (0-100)** | How often AI engines mention/cite your brand for industry queries, with a per-engine breakdown and confidence fields. |
| **Optimization Score (0-100)** | How AI-ready the site is across 61 page-level criteria. Strict grading: most sites land at 30-60. |

**Optimization weights:** Crawlability 25% + Content Structure 25% + Structured Data 20% + Authority 15% + AI Visibility 15%.
**Aggregation across pages ("weakest link"):** `0.6 * mean + 0.4 * min`, so inconsistent sites are penalized. Categories that could not be checked are excluded and the remaining weights are normalized, so a missing category never drags the score down.

### The 61 scoring criteria

| Category | IDs | Criteria |
|----------|-----|----------|
| **Crawlability** (12) | C1-C12 | AI-bot access in robots.txt for GPTBot, ClaudeBot, PerplexityBot, OAI-SearchBot, Claude-SearchBot, Bingbot, CCBot, Google-Extended; HTTP status; resource blockage; response time (TTFB); server-side rendering |
| **Content Structure** (13) | CS1-CS13 | Answer-first format, heading hierarchy, paragraph length, FAQ section, content length, readability, sentence-length variety, entity density, data density, statistics density, quotations, citations/references, content freshness |
| **Structured Data** (13) | SD1-SD13 | JSON-LD validation, Organization, Article, Person/Author, FAQPage, HowTo, Product/Offer, BreadcrumbList, ClaimReview, `sameAs` entity links, structured-data coverage, `llms.txt`, `llms-full.txt` |
| **Authority** (23) | A1-A8, S1-S15 | E-E-A-T composite, author bios with credentials, published/modified dates, Knowledge Graph, Wikidata QID, Wikipedia, review platform profiles, brand search signal, backlink / referring-domain proxies, plus SEO fundamentals: meta title and description, Open Graph, canonical tags, SSL/HTTPS, XML sitemap, mobile friendliness, Core Web Vitals (LCP), image alt text, internal linking, broken links, orphan pages, URL structure |

Each criterion returns a score, a human-readable reason and a status. Criteria that cannot be evaluated are marked *not checked* rather than scored 0.

### Extra analysis tools

- **Citability scoring**: scores passages for how likely an AI is to cite them. Weights: answer-block quality 30%, self-containment 25% (optimal passage length is about 134-167 words), structural readability 20%, statistical density 15%, uniqueness signals 10%.
- **llms.txt generator and validator**: builds `/llms.txt` and `/llms-full.txt` from your site structure.
- **Brand mention scanner**: checks presence on the platforms AI engines cite most (YouTube, Reddit, Wikipedia, LinkedIn). Brand mentions correlate more strongly with AI visibility than backlinks.
- **Code analysis (deep audit)**: upload up to 100 KB of site code/text and get an LLM-driven analysis plus generated fix prompts, alongside the basic URL-only audit.
- **Brand voice (Brand Signature)**: check whether new content matches a brand's voice. The design has 4 layers (rules, statistical fingerprint, pgvector semantic similarity, LLM deep analysis). Rules and semantic similarity work today. The other two are planned.
- **AI chat assistant**: ask questions about an audit and drill into issues (history capped at 20 messages).

### Recommendations

- Priority rules: **High** if `gap >= 50` or (`impact >= 200%` and `gap >= 30`); **Medium** if `impact >= 120%` and `gap >= 20`; otherwise **Low**.
- Each recommendation has a summary, action steps, estimated score impact, prior status (new / still open / resolved between audits), and is deduplicated by criterion + page hash.
- Sentiment-based recommendations and competitor-averaged gaps are included.
- Mark recommendations as implemented and re-audit to track the score delta.
- **Jira export**: customizable CSV (grouping, priority, fields, epic link) and direct ticket creation.

### Plans and limits

| | Free | Pro |
|---|------|-----|
| Audit | Partial: crawlability score, overall score, top 3 recommendations | Full audit, all categories, all recommendations, exports |
| Rate limit | 3 analyses/day | 100 (Enterprise tier: 1000) |
| Billing | n/a | Stripe checkout (monthly/yearly), webhook-driven subscription sync |

### Rules and guardrails

- **Cost cap:** every audit has a budget (`AUDIT_BUDGET_USD`, default $1.00). All LLM calls are recorded in a cost ledger and the audit stops spending at the cap.
- **AI response cache:** Redis, SHA-256 keys, 24 h TTL, fail-open.
- **Outbound rate limiting:** per provider (semaphore + token bucket), with concurrency caps per engine.
- **Auth:** JWT (access 30 min, refresh 7 days), bcrypt hashes. Password policy: 12+ characters with upper, lower, digit and special character.
- **Request limits:** 10 MB bodies and uploads; per-tier API rate limits by IP/user.
- **Security middleware stack** (outermost first): error sanitization, request size limit, security headers (CSP, HSTS, X-Frame-Options), request/audit logging, SQL-injection protection, API versioning, GZip, trusted hosts (production), CORS.
- **Competitor handling:** duplicate or empty competitor domains are de-duplicated and linked to brands.
- **Scoring honesty:** scorers never raise. Failures become "not checked" with a reason, never a fake score.

### API surface (`/api/v1`)

Auth (`/auth`) | Audits (`/audits`, queries CRUD, `/{id}/crawl`) | Dashboard + history + PDF/CSV export | Brands and multi-brand overview, share-of-voice trend | Competitors | Recommendations | Optimization | Reports | Chat | Code analysis | Payments (checkout, subscription status, webhook) | Integrations (Jira, Stripe) | Brand voice (`/voice`) | GEO data points. Full docs at `/api/v1/docs`.

### Frontend pages

Home, Analyze, Audit, Dashboard, Brands, Competitors, Recommendations, Optimization, Brand Voice, Pricing, Checkout (success/cancel), Settings, Login.

## Quick Start

### Prerequisites

- **Node.js**: v18+
- **Python**: 3.11+
- **Docker**: For Redis only (or install Redis natively)
- **Supabase Account**: Remote PostgreSQL database

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd geo-platform-mvp
   ```

2. **Setup Backend**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   # Edit .env with your Supabase DATABASE_URL and API keys
   ```

3. **Setup Frontend**
   ```bash
   cd frontend
   npm install
   cp .env.example .env
   # Edit .env with your Supabase URL
   ```

4. **Setup Database**
   - Create a Supabase project at https://supabase.com
   - Disable the Data API (Settings > API) — not needed
   - Enable pgvector extension via SQL Editor:
     ```sql
     CREATE EXTENSION IF NOT EXISTS vector;
     ```
   - Run migrations:
     ```bash
     cd backend && source venv/bin/activate && alembic upgrade head
     ```

### Running the Application

**One command (recommended):**
```bash
./start.sh
```

This starts Redis (Docker), runs migrations, launches the backend, Celery worker, and frontend.

**Manual (3 terminals):**

Terminal 1 — Redis:
```bash
docker run -d --name geo-redis -p 6379:6379 redis:7-alpine
```

Terminal 2 — Backend + Celery:
```bash
cd backend && source venv/bin/activate
uvicorn app.main:app --reload --port 8000 &
celery -A app.tasks.celery_app worker --loglevel=info -Q geo_platform,audit,analysis
```

Terminal 3 — Frontend:
```bash
cd frontend && npm run dev
```

Open **http://localhost:3000**, register an account, run an audit.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Nuxt 3 (Vue 3) + Tailwind CSS + Chart.js |
| Backend | FastAPI + SQLAlchemy + Pydantic v2 |
| Database | Supabase PostgreSQL + pgvector |
| Task Queue | Celery + Redis |
| AI Engines | LiteLLM (ChatGPT, Claude, Perplexity, Gemini, Mistral) |
| Payments | Stripe |
| Auth | JWT (PyJWT + pwdlib/bcrypt) |

## Project Structure

```
geo-platform-mvp/
├── start.sh                # One-command dev server launcher
├── backend/                # FastAPI Python backend
│   ├── app/
│   │   ├── api/           # API endpoints
│   │   ├── core/          # Config, security, middleware
│   │   ├── models/        # SQLAlchemy models
│   │   ├── services/      # Business logic (scoring/, citability, llmstxt, chat, ...)
│   │   └── tasks/         # Celery background tasks
│   ├── alembic/           # Database migrations (16)
│   ├── tests/             # pytest suite
│   └── requirements.txt
├── frontend/              # Nuxt 3 frontend
│   ├── components/        # Vue components
│   ├── pages/             # Route pages
│   ├── composables/       # Reusable logic
│   └── tests/e2e/         # Playwright E2E tests (45 tests)
├── docs/                  # Architecture, API reference, security, incidents
└── docker-compose.yml     # Redis + optional Docker dev setup
```

## Environment Variables

### Backend (`backend/.env`)
```env
DATABASE_URL=postgresql://postgres:PASSWORD@db.PROJECT_REF.supabase.co:5432/postgres
SUPABASE_URL=https://PROJECT_REF.supabase.co
SUPABASE_KEY=your-anon-key
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
GEMINI_API_KEY=...
PERPLEXITYAI_API_KEY=...
MISTRAL_API_KEY=...
# Optional: STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, JIRA_*
```

See `backend/.env.example` for the full list.

### Frontend (`frontend/.env`)
```env
NUXT_PUBLIC_API_BASE=http://localhost:8000/api/v1
NUXT_PUBLIC_SUPABASE_URL=https://PROJECT_REF.supabase.co
NUXT_PUBLIC_SUPABASE_KEY=your-anon-key
```

## Testing

```bash
# Backend tests
cd backend && source venv/bin/activate && pytest

# E2E tests (Playwright — mocked API, no backend needed)
cd frontend && npx playwright test

# Interactive test UI
cd frontend && npx playwright test --ui

# Frontend build check
cd frontend && npm run build
```

## API Documentation

Once the backend is running:
- **Swagger UI**: http://localhost:8000/api/v1/docs
- **Health**: http://localhost:8000/health

## Documentation

See [`docs/`](docs/): `ARCHITECTURE.md`, `API-REFERENCE.md`, `SECURITY.md`, `TESTING-STRATEGY.md`, `INCIDENTS.md`. Contributors should start with [`CLAUDE.md`](CLAUDE.md).

## License

Proprietary - All rights reserved
