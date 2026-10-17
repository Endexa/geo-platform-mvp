# GEO Platform MVP

A Generative Engine Optimization (GEO) platform that analyzes how well websites are optimized for AI language models (ChatGPT, Claude, Perplexity, Gemini, Mistral). Scores websites 0-100 across 61 criteria and generates optimization recommendations.

## Features

- **Site audits**: crawl a URL, score it on crawlability, structured data, content structure and authority
- **AI visibility**: query multiple AI engines and measure brand mentions, citations and sentiment
- **Competitor tracking** and brand linking
- **Citability scoring**, **llms.txt generation** and **brand scanning**
- **Recommendations** with Jira CSV export
- **Code analysis** flow and an **AI chat assistant** for audit results
- **PDF/HTML reports**, **Stripe** subscriptions and tiered rate limiting

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
