# Technology Stack

> Generated: 2026-02-21. Sources: `backend/requirements.txt`, `frontend/package.json`, `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`, `backend/app/core/config.py`, `backend/app/main.py`.

---

## Languages and Runtimes

| Layer | Language | Runtime Version |
|-------|----------|-----------------|
| Backend | Python | 3.12 (venv), 3.11+ declared in `backend/Dockerfile` |
| Frontend | TypeScript / Vue 3 | Node.js 18 (Alpine, declared in `frontend/Dockerfile`) |
| GEO Scripts | Python | 3.10+ (per `geo_data_points/requirements.txt` comment) |
| Migrations | Python (Alembic) | Shares backend runtime |

**Python runtime note:** The `backend/Dockerfile` pins `python:3.11-slim`. The local development `venv` at `backend/venv/` runs Python 3.12 (resolved from `site-packages/…/python3.12/`).

---

## Frameworks

### Backend — FastAPI

| Detail | Value |
|--------|-------|
| Framework | FastAPI |
| Version (requirements.txt) | `0.109.0` |
| Version (venv, actual installed) | `0.123.5` |
| ASGI server | Uvicorn `0.27.0` (requirements) / `0.38.0` (venv) |
| Entry point | `backend/app/main.py` |
| API prefix | `/api/v1` |
| Docs URL | `/api/v1/docs` (disabled unless `DEBUG=True`) |

**Routers registered in `backend/app/main.py`:**

| Router module | Prefix |
|---------------|--------|
| `app.api.analysis` | `/api/v1/analysis` |
| `app.api.optimization` | `/api/v1/optimization` |
| `app.api.brand_voice` | `/api/v1/voice` |
| `app.api.dashboard` | `/api/v1/dashboard` |
| `app.api.integrations` | `/api/v1/integrations` |
| `app.api.geo_datapoints` | `/api/v1/geo-datapoints` |

### Frontend — Nuxt 3

| Detail | Value |
|--------|-------|
| Framework | Nuxt 3 |
| Version (package.json) | `^3.9.0` |
| Mode | SPA (no SSR — all routes excluded from redirect in `nuxt.config.ts`) |
| Config file | `frontend/nuxt.config.ts` |
| Pages | `analyze.vue`, `brand-voice.vue`, `dashboard.vue`, `index.vue`, `login.vue`, `optimization.vue`, `settings.vue` |

---

## All Dependencies

### Backend Python Dependencies

From `backend/requirements.txt` (pinned versions listed) and actual installed versions from `backend/venv/` where they differ:

#### Web Framework and Server

| Package | requirements.txt | Venv (actual) |
|---------|-----------------|----------------|
| `fastapi` | `0.109.0` | `0.123.5` |
| `uvicorn[standard]` | `0.27.0` | `0.38.0` |
| `python-multipart` | `0.0.6` | — |

#### Database and ORM

| Package | requirements.txt | Venv (actual) | Purpose |
|---------|-----------------|----------------|---------|
| `sqlalchemy` | `2.0.25` | — | ORM |
| `alembic` | `1.13.1` | `1.17.2` | DB migrations |
| `psycopg2-binary` | `2.9.9` | — | PostgreSQL driver |
| `pgvector` | `0.2.4` | `0.4.1` | Vector column type for SQLAlchemy |

#### Supabase Client

| Package | requirements.txt | Venv (actual) |
|---------|-----------------|----------------|
| `supabase` | `2.3.0` | `2.24.0` |
| `postgrest-py` | `0.13.0` | (via supabase) |

#### Validation and Settings

| Package | requirements.txt | Venv (actual) |
|---------|-----------------|----------------|
| `pydantic` | `2.5.3` | `2.12.5` |
| `pydantic-settings` | `2.1.0` | `2.12.0` |

#### AI / LLM

| Package | requirements.txt | Venv (actual) | Purpose |
|---------|-----------------|----------------|---------|
| `litellm` | `1.17.0` | `1.80.7` | LLM abstraction layer |
| `langchain` | `1.0.0` | not installed | RAG framework (listed but not in venv) |
| `langchain-openai` | `0.0.2` | not installed | LangChain OpenAI adapter (listed but not in venv) |
| `openai` | `1.7.0` | `2.8.1` | OpenAI Python client |
| `tiktoken` | `0.5.2` | — | Token counting for OpenAI |

#### Vector Embeddings

| Package | requirements.txt | Venv (actual) | Purpose |
|---------|-----------------|----------------|---------|
| `sentence-transformers` | `2.2.2` | not in venv | Embedding generation (listed but not installed) |
| `huggingface_hub` | (transitive) | `1.1.7` | HuggingFace model hub client |
| `tokenizers` | (transitive) | `0.22.1` | Fast tokenization |
| `numpy` | (transitive) | `2.3.5` | Numerical arrays |

#### Task Queue

| Package | requirements.txt | Venv (actual) |
|---------|-----------------|----------------|
| `celery` | `5.3.4` | `5.6.0` |
| `redis` | `5.0.1` | `7.1.0` |

#### Web Scraping

| Package | requirements.txt | Venv (actual) | Purpose |
|---------|-----------------|----------------|---------|
| `playwright` | `1.41.0` | `1.56.0` | Headless browser (listed; used in `AnalyzerService` as planned upgrade path) |
| `beautifulsoup4` | `4.12.2` | `4.14.3` | HTML parsing |
| `lxml` | `5.1.0` | — | XML/HTML parser backend |
| `requests` | `2.31.0` | — | HTTP client |

#### Text Processing

| Package | requirements.txt | Venv (actual) | Purpose |
|---------|-----------------|----------------|---------|
| `python-readability` | `0.3.0` | — | Article extraction |
| `textstat` | `0.7.3` | — | Flesch-Kincaid readability scoring |
| `nltk` | (transitive) | `3.9.2` | NLP toolkit |

#### Authentication and Security

| Package | requirements.txt | Venv (actual) | Purpose |
|---------|-----------------|----------------|---------|
| `python-jose[cryptography]` | `3.3.0` | — | JWT encoding/decoding |
| `passlib[bcrypt]` | `1.7.4` | — | Password hashing (bcrypt) |
| `cryptography` | (transitive) | — | Cryptography primitives |

#### HTTP and Utilities

| Package | requirements.txt | Venv (actual) |
|---------|-----------------|----------------|
| `httpx` | `0.26.0` | — |
| `python-dotenv` | `1.0.0` | — |

#### Payment Processing

| Package | requirements.txt | Venv (actual) |
|---------|-----------------|----------------|
| `stripe` | `7.9.0` | `14.0.1` |

#### Monitoring and Logging

| Package | requirements.txt | Venv (actual) | Purpose |
|---------|-----------------|----------------|---------|
| `loguru` | `0.7.2` | `0.7.3` | Structured logging |
| `sentry-sdk` | `1.39.0` | `2.47.0` | Error monitoring |

#### Testing

| Package | requirements.txt | Purpose |
|---------|-----------------|---------|
| `pytest` | `7.4.3` | Test runner |
| `pytest-asyncio` | `0.23.2` | Async test support |

#### Additional Venv-Only Packages (transitives worth noting)

| Package | Venv version | Source |
|---------|-------------|--------|
| `pandas` | installed | transitive |
| `openpyxl` | installed | transitive |
| `aiohttp` | installed | transitive (LiteLLM/Supabase) |
| `httpcore` | installed | transitive (httpx) |
| `grpcio` | installed | transitive |

---

### Frontend JavaScript Dependencies

From `frontend/package.json`:

#### Runtime Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `nuxt` | `^3.9.0` | Full-stack Vue framework |
| `vue` | `^3.4.0` | UI rendering |
| `vue-router` | `^4.2.5` | Client-side routing |
| `pinia` | `^2.1.7` | State management |
| `@pinia/nuxt` | `^0.5.1` | Pinia Nuxt module |
| `@nuxtjs/supabase` | `^1.1.6` | Supabase Nuxt integration |
| `@headlessui/vue` | `^1.7.16` | Accessible UI primitives |
| `@heroicons/vue` | `^2.0.18` | SVG icon set |
| `lucide-vue-next` | `^0.294.0` | Additional SVG icons |
| `chart.js` | `^4.4.1` | Chart rendering |
| `vue-chartjs` | `^5.3.0` | Vue wrapper for Chart.js |
| `@vueuse/core` | `^10.7.0` | Vue composition utilities |

#### Development Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `@nuxtjs/tailwindcss` | `^6.10.4` | Tailwind CSS Nuxt module |
| `tailwindcss` | `^3.4.0` | Utility-first CSS framework |
| `autoprefixer` | `^10.4.16` | PostCSS vendor prefix plugin |
| `postcss` | `^8.4.32` | CSS transformation |
| `typescript` | `^5.3.3` | TypeScript compiler |
| `@types/node` | `^20.10.6` | Node.js type definitions |

#### Nuxt Modules (configured in `frontend/nuxt.config.ts`)

```typescript
modules: [
  '@nuxtjs/tailwindcss',  // Tailwind CSS integration
  '@pinia/nuxt',          // State management
  '@nuxtjs/supabase'      // Auth + data (redirect disabled for MVP)
]
```

---

### GEO Data Points Module Dependencies

From `geo_data_points/requirements.txt`:

| Package | Version | Purpose |
|---------|---------|---------|
| `sqlalchemy` | `2.0.25` | ORM for results storage |
| `psycopg2-binary` | `2.9.9` | PostgreSQL driver |
| `requests` | `2.31.0` | HTTP client for measurements |
| `beautifulsoup4` | `4.12.2` | HTML parsing |
| `lxml` | `5.1.0` | Parser backend |
| `textstat` | `0.7.3` | Text analysis |
| `python-dotenv` | `1.0.0` | Environment loading |

---

## Configuration Approach

### Environment Variables

Configuration is loaded via Pydantic Settings (`pydantic-settings`) in `backend/app/core/config.py`. All settings are declared as class attributes on the `Settings(BaseSettings)` class with `env_file = ".env"`.

**Primary env file:** `backend/.env` (not committed; template at `.env.example`)

Full variable list:

```
# Core
DATABASE_URL          postgresql://postgres:postgres@localhost:5432/geo_platform
REDIS_URL             redis://localhost:6379/0
SECRET_KEY            <random hex 32>

# Auth
ALGORITHM             HS256 (default)
ACCESS_TOKEN_EXPIRE_MINUTES   30 (default)
REFRESH_TOKEN_EXPIRE_DAYS     7 (default)

# External APIs
OPENAI_API_KEY        required
ANTHROPIC_API_KEY     optional
AHREFS_API_KEY        optional
SEMRUSH_API_KEY       optional
GOOGLE_PAGESPEED_API_KEY      optional

# Supabase
SUPABASE_URL          required
SUPABASE_KEY          required (anon key)
SUPABASE_SERVICE_KEY  optional

# Payments
STRIPE_SECRET_KEY     optional
STRIPE_WEBHOOK_SECRET optional

# Jira
JIRA_BASE_URL         optional
JIRA_EMAIL            optional
JIRA_API_TOKEN        optional

# Monitoring
SENTRY_DSN            optional

# Feature flags
ENABLE_RATE_LIMITING  true
ENABLE_API_KEYS       true
ENABLE_WEBHOOKS       true
ENABLE_SECURITY_HEADERS       true
ENABLE_AUDIT_LOGGING  true
ENABLE_METRICS        true
ENABLE_CSRF_PROTECTION        true

# GEO data points engine
GEO_REQUEST_TIMEOUT   10
GEO_MAX_RETRIES       3
GEO_ENABLE_EXTERNAL_APIS      false
GEO_PARALLEL_EXECUTION        true
GEO_MAX_WORKERS       4

# Embeddings
EMBEDDING_MODEL       text-embedding-3-small
EMBEDDING_DIMENSION   1536

# Frontend (Nuxt runtimeConfig)
NUXT_PUBLIC_API_URL           http://localhost:8000
NUXT_PUBLIC_SUPABASE_URL      <supabase url>
NUXT_PUBLIC_SUPABASE_KEY      <supabase anon key>
```

### Config Files

| File | Purpose |
|------|---------|
| `backend/app/core/config.py` | Pydantic Settings class — single source of truth for backend config |
| `backend/.env` | Local secrets (git-ignored) |
| `.env.example` | Root-level template for all env vars |
| `frontend/nuxt.config.ts` | Nuxt runtime config, module registration, Supabase options |
| `frontend/tailwind.config.js` | Design system color tokens (primary blues, success, warning, danger) |
| `docker-compose.yml` | Service definitions, env injection, networking |

---

## Build Tools

### Backend

| Tool | Version | Purpose |
|------|---------|---------|
| `pip` | (venv) | Package manager |
| `uvicorn` | `0.27.0` / `0.38.0` | ASGI server — hot reload in dev |
| `alembic` | `1.13.1` / `1.17.2` | Schema migration runner |
| Docker (`python:3.11-slim`) | — | Container build |

**Build command:**
```bash
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Migration command:**
```bash
cd backend && alembic upgrade head
```

### Frontend

| Tool | Version | Purpose |
|------|---------|---------|
| `npm` | (Node 18) | Package manager |
| `nuxt` CLI | `^3.9.0` | Dev server, build, generate |
| `postcss` + `autoprefixer` | `^8.4.32` / `^10.4.16` | CSS processing |
| Docker (`node:18-alpine`) | — | Container build |

**Build commands:**
```bash
cd frontend
npm install
npm run dev        # Dev server on :3000
npm run build      # Production build
npm run generate   # Static site generation
```

---

## Dev Tools and Quality

| Tool | Location | Purpose |
|------|----------|---------|
| `pytest` + `pytest-asyncio` | `backend/` | Backend unit and async tests |
| ESLint | `frontend/` (`npm run lint`) | Frontend linting |
| `alembic` | `backend/` | Database schema versioning |
| Loguru file rotation | `backend/logs/app.log` | 500MB rotation, 10-day retention, gzip compression |
| Sentry SDK | Backend | Error monitoring (configured via `SENTRY_DSN`) |
| Nuxt DevTools | Frontend | Enabled in `nuxt.config.ts` (`devtools: { enabled: true }`) |

---

## Infrastructure and Containers

### Docker Compose Services (`docker-compose.yml`)

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| `postgres` | `ankane/pgvector:latest` | `5432` | PostgreSQL with pgvector extension |
| `redis` | `redis:7-alpine` | `6379` | Cache + Celery broker |
| `backend` | Custom (`backend/Dockerfile`) | `8000` | FastAPI application |
| `celery` | Custom (`backend/Dockerfile`) | — | Background task worker |
| `frontend` | Custom (`frontend/Dockerfile`) | `3000` | Nuxt 3 dev server |

### Database Schema

PostgreSQL database `geo_platform` with tables managed by SQLAlchemy's `Base.metadata.create_all()` on startup (no Alembic used for current MVP tables):

| Table | Model file | Description |
|-------|------------|-------------|
| `organizations` | `backend/app/models/organization.py` | Tenant model; holds Stripe tier |
| `profiles` | `backend/app/models/profile.py` | User model; links to org |
| `websites` | `backend/app/models/website.py` | Tracked URLs per org |
| `analyses` | `backend/app/models/analysis.py` | Analysis runs (scores in JSONB) |
| `recommendations` | `backend/app/models/recommendation.py` | AI-generated action items |
| `brand_voice_configs` | `backend/app/models/brand_voice.py` | Brand voice configurations |
| `voice_vectors` | `backend/app/models/brand_voice.py` | pgvector embeddings (1536-dim) |
| `voice_rules` | `backend/app/models/brand_voice.py` | Rule-based brand constraints |

### SQLAlchemy Connection Pool

Configured in `backend/app/core/database.py`:

```python
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,       # DB_POOL_SIZE setting
    max_overflow=20     # DB_MAX_OVERFLOW setting
)
```

### Celery Task Queue

- **Broker:** Redis (`REDIS_URL`)
- **Worker start:** `celery -A app.tasks.celery_app worker --loglevel=info`
- **Rate limiting backend:** Redis (sliding window counters in `backend/app/core/rate_limiter.py`)

---

## Middleware Stack

Applied in `backend/app/main.py` (outermost to innermost):

```
1. ErrorSanitizationMiddleware     — sanitize error responses in production
2. RequestSizeLimitMiddleware       — reject bodies > 10MB
3. SecurityHeadersMiddleware        — CSP, HSTS, X-Frame-Options, Referrer-Policy
4. RequestLoggingMiddleware         — per-request ID, duration logging
5. AuditLogMiddleware               — detailed logging for sensitive endpoints
6. SQLInjectionProtectionMiddleware — keyword detection in query strings
7. APIVersionMiddleware             — enforce /api/v1/ prefix
8. GZipMiddleware                   — compress responses > 1000 bytes
9. TrustedHostMiddleware            — production only
10. CORSMiddleware                  — innermost; default origin: localhost:3000
```

All middleware classes defined in `backend/app/core/middleware.py`.

---

## Security Infrastructure

| Feature | Implementation | Status |
|---------|----------------|--------|
| JWT auth | `python-jose` HS256, `passlib` bcrypt | Code ready in `backend/app/core/security.py` — **disabled** (endpoints have auth commented out) |
| API keys | SHA-256 hashed, `X-API-Key` header | Stub — verification not implemented |
| Rate limiting | Redis sliding window, per IP/user/endpoint | Active |
| Password policy | Min 12 chars, upper+lower+digit+special | Config defined; not enforced (no auth yet) |
| Webhook signatures | HMAC-SHA256 | Active for Stripe webhook |
| Role-based access | `RoleChecker` / `OrganizationChecker` dependencies | Code ready, not wired |
| Request size limit | 10MB hard cap | Active |
| SQL injection guard | Keyword scan on query strings | Active |
| Tier-based rate limits | Free: 3/day, Pro: 100/day, Enterprise: 1000/day | Config defined; tier detection not wired |
