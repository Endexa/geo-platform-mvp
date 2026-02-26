# Architecture — GEO Platform MVP

> Generated: 2026-02-21. Source of truth for system design, data flow, and layer contracts.

---

## 1. System Overview

GEO Platform is a Generative Engine Optimization tool. It scores websites 0–100 across 7 modules by measuring how well a site is indexed and understood by AI language models (ChatGPT, Claude, Perplexity, Bing Copilot).

**Architecture Pattern:** Three-tier web application

```
┌──────────────────────────────────────────────────────────────┐
│  Browser                                                      │
│  Nuxt 3 SPA (Vue 3 + TypeScript + Tailwind CSS)              │
│  Port 3000                                                    │
└────────────────────────┬─────────────────────────────────────┘
                         │ HTTP/JSON (fetch API)
                         │ Base URL: NUXT_PUBLIC_API_URL
                         ▼
┌──────────────────────────────────────────────────────────────┐
│  FastAPI Application                                          │
│  Python 3.12 · Uvicorn · Port 8000                           │
│  Entry point: backend/app/main.py                            │
│  Prefix: /api/v1/                                            │
└─────┬──────────────────┬────────────────────────────────────┘
      │                  │
      │ SQLAlchemy       │ redis-py
      ▼                  ▼
┌──────────┐      ┌────────────────┐      ┌──────────────────┐
│ PostgreSQL│      │ Redis 7        │      │ Celery Worker    │
│ 15+       │      │ Port 6379      │      │ (declared in     │
│ + pgvector│      │ Rate limiting  │      │ docker-compose,  │
│ Port 5432 │      │ cache         │      │ not wired to     │
└──────────┘      └────────────────┘      │ analysis yet)    │
                                          └──────────────────┘
```

**Deployment:** Docker Compose with five services — `postgres`, `redis`, `backend`, `celery`, `frontend`. See `/home/salim/Informatique/Perso/Endexa/geo-platform-mvp/docker-compose.yml`.

---

## 2. Backend Layer Architecture

The backend follows a strict four-layer stack. Each layer has one responsibility and calls only the layer below it.

```
HTTP Request
     │
     ▼
┌──────────────────────────────────────────────────────┐
│  Layer 1: Middleware Stack (core/middleware.py)        │
│  Runs on EVERY request before routing                 │
└──────────────────────┬───────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────┐
│  Layer 2: API Routers (api/*.py)                      │
│  FastAPI route handlers. Input validation.            │
│  Returns HTTP responses. Calls services.              │
└──────────────────────┬───────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────┐
│  Layer 3: Services (services/*.py)                    │
│  Business logic. LLM calls. Scoring algorithms.       │
│  No HTTP knowledge. Calls models / ORM.               │
└──────────────────────┬───────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────┐
│  Layer 4: Models (models/*.py)                        │
│  SQLAlchemy ORM models. Database schema definitions.  │
│  No business logic. Pure data structure.              │
└──────────────────────┬───────────────────────────────┘
                       │
                       ▼
                  PostgreSQL + pgvector
```

### Layer Contracts

| Layer | File(s) | Receives | Returns |
|-------|---------|----------|---------|
| Middleware | `core/middleware.py` | ASGI Request | ASGI Response / raises HTTPException |
| API Router | `api/*.py` | Pydantic request model + `Session` dep | `dict` or Pydantic response model |
| Service | `services/*.py` | `Session` + raw Python values | `dict` or Pydantic model |
| Model | `models/*.py` | SQLAlchemy session operations | SQLAlchemy ORM instances |

---

## 3. Middleware Stack

Defined in `backend/app/main.py`. **Order is critical** — FastAPI/Starlette executes middleware in reverse registration order (last added = outermost in request processing).

```
Inbound Request
       │
       ▼   (outermost)
┌─────────────────────────────────────┐
│ 1. ErrorSanitizationMiddleware      │  Catches all unhandled exceptions.
│    Hides stack traces in production │  Returns generic 500 JSON.
├─────────────────────────────────────┤
│ 2. RequestSizeLimitMiddleware       │  Rejects bodies > 10 MB (413).
├─────────────────────────────────────┤
│ 3. SecurityHeadersMiddleware        │  Adds CSP, HSTS, X-Frame-Options,
│    (if ENABLE_SECURITY_HEADERS)     │  X-Content-Type-Options, etc.
├─────────────────────────────────────┤
│ 4. RequestLoggingMiddleware         │  Assigns UUID request_id.
│    (if ENABLE_AUDIT_LOGGING)        │  Logs method, path, IP, duration.
├─────────────────────────────────────┤
│ 5. AuditLogMiddleware               │  Detailed log for sensitive paths:
│    (if ENABLE_AUDIT_LOGGING)        │  /analyze, /voice/config, /integrations
├─────────────────────────────────────┤
│ 6. SQLInjectionProtectionMiddleware │  Scans query-string for SQL keywords.
│                                     │  Returns 400 on match.
├─────────────────────────────────────┤
│ 7. APIVersionMiddleware             │  Rejects /api/ without /v1/.
│                                     │  Adds X-API-Version: 1.0 header.
├─────────────────────────────────────┤
│ 8. GZipMiddleware                   │  Compresses responses > 1 KB.
├─────────────────────────────────────┤
│ 9. TrustedHostMiddleware            │  Production only: validates Host header.
├─────────────────────────────────────┤
│ 10. CORSMiddleware      (innermost) │  Handles CORS. Allows configured origins.
└─────────────────────────────────────┘
       │
       ▼
   Route Handler
```

Source file: `/home/salim/Informatique/Perso/Endexa/geo-platform-mvp/backend/app/core/middleware.py`

---

## 4. API Surface

All routes are prefixed with `/api/v1/`. Registered in `backend/app/main.py`.

| Router File | Prefix | Tags | Key Endpoints |
|-------------|--------|------|---------------|
| `api/analysis.py` | `/api/v1/analysis` | analysis | `POST /analyze`, `GET /{id}`, `GET /{id}/recommendations` |
| `api/optimization.py` | `/api/v1/optimization` | optimization | `POST /generate`, `POST /optimize-content`, `PATCH /{id}/implement` |
| `api/brand_voice.py` | `/api/v1/voice` | brand-voice | `POST /config`, `POST /config/{id}/upload`, `POST /config/{id}/rule`, `POST /check`, `GET /config/{id}` |
| `api/dashboard.py` | `/api/v1/dashboard` | dashboard | `GET /stats`, `GET /history` |
| `api/integrations.py` | `/api/v1/integrations` | integrations | `POST /jira/create-ticket`, `POST /stripe/create-checkout`, `POST /stripe/webhook` |
| `api/geo_datapoints.py` | `/api/v1/geo-datapoints` | geo-datapoints | `POST /run`, `GET /{id}`, `GET /{id}/summary`, `GET /{id}/module/{module}` |

Non-prefixed system endpoints (on `app` directly):

| Path | Purpose |
|------|---------|
| `GET /` | API info + security status |
| `GET /health` | Health check for monitoring |
| `GET /security-info` | Security config (dev only) |
| `GET /api/v1/docs` | Swagger UI (DEBUG=true only) |

---

## 5. Database Schema

Single PostgreSQL database (`geo_platform`) with two independent schemas — one from SQLAlchemy models (backend), one from the geo_data_points module.

### Backend Schema (SQLAlchemy, `backend/app/models/`)

```
organizations
├── id          UUID PK
├── name        String
├── subscription_tier  String (free|pro|enterprise)
└── stripe_customer_id String?

profiles
├── id          UUID PK  ← links to Supabase auth.users
├── org_id      UUID FK → organizations
├── full_name   String?
└── role        String (member|admin|owner)

websites
├── id          UUID PK
├── org_id      UUID FK → organizations  (nullable in MVP)
├── domain      String
├── sitemap_url String?
└── last_crawled_at  DateTime?

analyses
├── id              UUID PK
├── website_id      UUID FK → websites
├── status          String (pending|processing|completed|failed)
├── geo_score       Integer? (0–100)
├── visibility_score  Integer? (0–100)
├── readability_score Integer? (0–100)
├── authority_score   Integer? (0–100)
├── raw_data        JSONB?
├── created_at      DateTime
└── completed_at    DateTime?

recommendations
├── id              UUID PK
├── analysis_id     UUID FK → analyses
├── category        String (content|technical|metadata)
├── severity        String (high|medium|low)
├── issue           Text
├── action_plan     Text
├── impact_score    String?
├── implemented     Boolean
└── jira_ticket_id  String?

brand_voice_configs
├── id          UUID PK
├── org_id      UUID FK → organizations
├── name        String
└── description Text?

voice_vectors
├── id              UUID PK
├── config_id       UUID FK → brand_voice_configs
├── content_chunk   Text
└── embedding       Vector(1536)   ← pgvector, OpenAI text-embedding-3-small

voice_rules
├── id          UUID PK
├── config_id   UUID FK → brand_voice_configs
├── rule_type   String (forbidden_word|required_phrase|tone_directive)
└── value       Text
```

### geo_data_points Schema (SQLAlchemy, `geo_data_points/db/models.py`)

```
geo_analyses                        ← separate from "analyses" table above
├── id                  UUID PK
├── site_url            String
├── status              String (pending|running|completed|failed)
├── timestamp           DateTime
├── created_at          DateTime
├── completed_at        DateTime?
├── total_data_points   Integer
├── successful_measurements Integer
├── failed_measurements  Integer
└── average_score       Float?

geo_data_point_results
├── id                  UUID PK
├── analysis_id         UUID FK → geo_analyses
├── data_point_name     String
├── module              String (WI|CNT|BV|SEO|UX|COMP|LEG)
├── priority            String (High|Med|Low)
├── score               Float (0–100)
├── comment             Text
├── measurement_method  String?
├── automation_level    String?  (Full|Semi)
├── execution_time_ms   Float?
├── error_message       Text?
└── created_at          DateTime
```

**Note:** The two database schemas live in the same PostgreSQL instance but use separate SQLAlchemy `Base` objects and are not foreign-key linked to each other.

---

## 6. Data Flow Diagrams

### 6.1 URL Analysis Flow (Main Feature)

```
Frontend /analyze page
        │
        │ POST /api/v1/analysis/analyze
        │ { url, keywords }
        ▼
api/analysis.py → create_analysis()
        │
        ├── 1. Validate URL (URLValidator — blocks localhost, private IPs)
        ├── 2. Validate keywords (KeywordValidator — max 50, sanitized)
        ├── 3. Query or create Website record (by domain)
        ├── 4. Create Analysis record (status="pending")
        ├── 5. Add background task: AnalyzerService.run_analysis()
        └── 6. Return { analysis_id, status: "pending" }
                │
                │ (async background task via FastAPI BackgroundTasks)
                ▼
        AnalyzerService.run_analysis()  [services/analyzer.py]
                │
                ├── Set status = "processing"
                ├── fetch_content(url)
                │     └── requests.get() + BeautifulSoup
                │         Extracts: text, h1_count, h2_count, headings[]
                ├── calculate_visibility_score()
                │     └── keywords found in headings / total keywords × 100
                ├── calculate_readability_score()
                │     └── textstat.flesch_reading_ease() normalized 0–100
                ├── calculate_authority_score()
                │     └── MOCK: .edu/.gov=85, known sites=75, else random 40-70
                ├── geo_score = (visibility×0.4 + readability×0.3 + authority×0.3)
                └── Set status = "completed", save scores + raw_data

Frontend polls GET /api/v1/analysis/{id} every 2 seconds
        │
        └── Returns { status, geo_score, visibility_score, ... }
            Frontend shows score cards when status === "completed"
```

### 6.2 GEO Data Points Flow (OLD System — Connected)

This is the system wired to the API via `api/geo_datapoints.py`.

```
POST /api/v1/geo-datapoints/run
        │
        ▼
api/geo_datapoints.py → run_geo_analysis()
        │
        ├── Imports: GeoOrchestrator from geo_data_points/orchestrator/run_all.py
        ├── Creates pending geo_analyses record
        └── Starts background task: GeoOrchestrator.run_all()
                │
                ▼
        GeoOrchestrator.run_all()
                │
                ├── Load data_points.json (108 data point definitions)
                ├── For each data point:
                │     ├── Convert name to module path: "scripts.<module_name>"
                │     │     e.g. "Robots.txt - GPTBot" → "scripts.robots_txt_gptbot"
                │     ├── importlib.import_module("scripts.robots_txt_gptbot")
                │     ├── Instantiate class (e.g. RobotsTxtGPTBot(url))
                │     └── Call .run() → { score, comment, metadata, ... }
                │
                │   Classes in scripts/ inherit from scripts/base_measurement.py:
                │   - synchronous measure() method
                │   - uses utils.get_base_url(), utils.get_logger()
                │
                ├── Store each DataPointResult in geo_data_point_results table
                └── Update geo_analyses: status="completed", average_score

GET /api/v1/geo-datapoints/{id}         → returns all results
GET /api/v1/geo-datapoints/{id}/summary → aggregated by module
GET /api/v1/geo-datapoints/{id}/module/{module} → filtered by module
```

### 6.3 GEO Data Points Flow (NEW System — Disconnected)

The `measurements/` directory contains 99 scripts built against a different interface. **Nothing calls these scripts.** They have no orchestrator, no API wiring.

```
geo_data_points/measurements/*.py
        │
        Implements: geo_data_points.base.BaseMeasurement (base.py at root)
        Interface:  async measure(url, html, metadata) → Dict
        Pattern:    Each file exports a singleton: measurement = XyzMeasurement()
        │
        NOT connected to:
        - orchestrator/run_all.py  (which imports from scripts/ not measurements/)
        - api/geo_datapoints.py    (which calls GeoOrchestrator)
        - any celery task
        - any test runner
        │
        Only tested by: test_all_measurements.py at project root
        (standalone script, not wired to FastAPI)
```

### 6.4 Brand Voice Flow

```
POST /api/v1/voice/config         → Create BrandVoiceConfig record
POST /api/v1/voice/config/{id}/upload  → Upload knowledge base text
        │
        ▼
BrandVoiceService.process_knowledge_base()
        ├── Chunk text into ~500 char paragraphs
        ├── For each chunk: openai.embeddings.create(model="text-embedding-3-small")
        └── Store VoiceVector(content_chunk, embedding[1536]) in DB

POST /api/v1/voice/config/{id}/rule → Add VoiceRule (forbidden_word etc.)

POST /api/v1/voice/check
        │
        ▼
BrandVoiceService.check_voice()
        ├── Layer 1: RULES ENGINE (synchronous)
        │     ├── _check_rules(): iterates VoiceRule records
        │     ├── forbidden_word: -20 pts per violation
        │     ├── required_phrase: -10 pts per missing phrase
        │     └── Returns rule_score (0–100), violations[], suggestions[]
        │
        ├── Layer 3: SEMANTIC SIMILARITY (async)
        │     ├── Generate embedding for input text (OpenAI API)
        │     ├── pgvector cosine similarity: embedding <=> stored_embedding
        │     ├── Average top-5 similarities → vector_score (0–100)
        │     └── SQL: SELECT 1 - (embedding <=> ?) as similarity FROM voice_vectors
        │
        └── hybrid_score = (vector_score × 0.7) + (rule_score × 0.3)

Note: Layer 2 (Statistical Fingerprint) and Layer 4 (LLM Deep Analysis) are
planned but not implemented. See CLAUDE.md for the 4-layer architecture target.
```

---

## 7. Security Architecture

### Input Validation

All request models inherit from `SecureBaseModel` (Pydantic, `extra="forbid"`). Validators live in `backend/app/core/validators.py`:

| Validator | Purpose |
|-----------|---------|
| `URLValidator` | Blocks localhost, RFC-1918 IPs, `javascript:`, `data:`, `file:` schemes (SSRF protection) |
| `StringSanitizer` | Detects SQL injection and XSS patterns via regex. Strips null bytes. |
| `KeywordValidator` | Max 50 keywords, max 100 chars each, alphanumeric + spaces only |
| `FileUploadValidator` | Allowed: `.txt`, `.pdf`, `.doc`, `.docx`. Max 10 MB. Blocks path traversal. |
| `PasswordValidator` | Min 12 chars, requires upper+lower+digit+special |

### Rate Limiting

Redis-backed sliding window counters. Defined in `backend/app/core/rate_limiter.py`:

| Limiter | Limit | Applied To |
|---------|-------|-----------|
| `standard_rate_limit` | 100 req / 60s per IP | Dashboard, brand voice read, geo-datapoints read |
| `analysis_rate_limit` | 3 req / 5 min per IP+endpoint | `POST /analyze`, `POST /geo-datapoints/run` |
| `optimization_rate_limit` | 10 req / 60s | `POST /optimization/generate` |
| `upload_rate_limit` | 5 req / 1 hour | `POST /voice/config/{id}/upload` |
| `integration_rate_limit` | 20 req / 60s | Jira, Stripe endpoints |

### Authentication (Ready but Disabled)

JWT + Supabase auth is implemented in `backend/app/core/security.py` but **commented out** on all endpoints for MVP. The dependency injection pattern is in place:

```python
# In every router — ready to enable:
# current_user: Profile = Depends(get_current_active_user)
# org: Organization = Depends(OrganizationChecker())
```

Role checking: `RoleChecker(["admin", "owner"])`, `OrganizationChecker(required_tier="pro")`.

---

## 8. The Dual GEO Data Points Architecture Problem

**This is the most important architectural issue in the codebase.** There are two completely separate, incompatible systems for running the 108 GEO measurements.

### System A — OLD (`scripts/`): 5 scripts, connected to the API

```
geo_data_points/
└── scripts/
    ├── base_measurement.py          ← synchronous BaseMeasurement
    ├── robots_txt_gptbot.py         ← class RobotsTxtGPTBot(BaseMeasurement)
    ├── robots_txt_claudebot.py      ← class RobotsTxtClaudebot(BaseMeasurement)
    ├── schema_org_organization.py   ← class SchemaOrgOrganization(BaseMeasurement)
    ├── response_time.py             ← class ResponseTime(BaseMeasurement)
    └── title_tag_optimization.py    ← class TitleTagOptimization(BaseMeasurement)
```

**Interface contract (OLD):**
```python
class BaseMeasurement(ABC):
    def __init__(self, url: str): ...           # takes URL in constructor
    @abstractmethod
    def measure(self) -> Dict[str, Any]: ...    # synchronous
    def run(self) -> Dict[str, Any]: ...        # calls measure(), adds timing
```

**Wired to:** `orchestrator/run_all.py` → `GeoOrchestrator` → imported by `api/geo_datapoints.py`

**How the orchestrator discovers scripts:**
```python
# In orchestrator/run_all.py:
module_path = f"scripts.{module_name}"       # e.g. "scripts.robots_txt_gptbot"
module = importlib.import_module(module_path)
class_name = self._get_measurement_class_name(module_name)  # "RobotsTxtGptbot"
measurement_class = getattr(module, class_name)
measurement = measurement_class(self.url)
result = measurement.run()
```

**Status:** Working for the 5 implemented scripts. For the other 103 data points, the orchestrator gracefully returns `score: 0.0` with message `"Script not implemented yet: <name>.py"`.

---

### System B — NEW (`measurements/`): 99 scripts, disconnected

```
geo_data_points/
├── base.py                          ← DIFFERENT BaseMeasurement (async)
└── measurements/
    ├── base_measurement.py          ← ANOTHER base class (simpler)
    ├── wi_*.py  (26 files)          ← Web Infrastructure
    ├── cnt_*.py (21 files)          ← Content
    ├── bv_*.py  (15 files)          ← Brand Visibility
    ├── seo_*.py (12 files)          ← SEO
    ├── ux_*.py  (8 files)           ← UX
    ├── comp_*.py (8 files)          ← Competitive
    └── leg_*.py (5 files)           ← Legal
    Total: ~99 measurement scripts
```

**Interface contract (NEW):**
```python
# From geo_data_points/base.py:
class BaseMeasurement(ABC):
    def __init__(self, code, name, description, category, weight=1.0): ...
    @abstractmethod
    async def measure(self, url, html=None, metadata=None) -> Dict: ...  # ASYNC
    async def execute(self, url, html=None, metadata=None) -> Dict: ...  # wrapper

# Usage pattern (each file ends with):
measurement = RobotsTxtBingbotMeasurement()   # singleton export
```

**NOT wired to:** Anything. No orchestrator calls `measurements/`. No API route triggers them.

**Imports:** Use `from geo_data_points.base import BaseMeasurement` and `from geo_data_points.utils.http_client import CachedSession`, which requires the package to be importable as `geo_data_points`.

**Test coverage:** `test_all_measurements.py` at the project root runs them standalone, but this is not integrated into any CI or API flow.

---

### Comparison Table

| Dimension | OLD (scripts/) | NEW (measurements/) |
|-----------|---------------|---------------------|
| Count | 5 scripts | ~99 scripts |
| Base class | `scripts/base_measurement.py` | `geo_data_points/base.py` |
| Interface | `__init__(url)`, sync `measure()` | `__init__(code, name, ...)`, async `measure(url, html, metadata)` |
| Singleton export | No | Yes (`measurement = XyzMeasurement()`) |
| Connected to API | Yes (via orchestrator) | No |
| Connected to orchestrator | Yes | No |
| Database storage | Yes (geo_data_point_results) | No |
| Working results | 5 scripts return real data | All disconnected |
| How discovered | `importlib.import_module("scripts.<name>")` | Not discovered |

### Resolution Path

To connect the NEW system, one of these approaches is needed:

**Option A — Rewrite orchestrator:** Update `orchestrator/run_all.py` to import from `measurements/` using the async `execute()` interface. Requires `asyncio.run()` wrapper or rewrite to async.

**Option B — Adapter layer:** Add a thin sync wrapper in `scripts/` for each measurement in `measurements/` that bridges the interface gap.

**Option C — New orchestrator:** Create `orchestrator/run_all_async.py` that uses `asyncio.gather()` to run all 99 new measurements in parallel and stores to DB.

---

## 9. Frontend Architecture

**Pattern:** Nuxt 3 SPA (no SSR). All pages are client-rendered. The `ssr: false` default is achieved by not configuring SSR, and Nuxt's `redirect: false` disables auth-guard redirects.

**Nuxt modules used:** `@nuxtjs/tailwindcss`, `@pinia/nuxt`, `@nuxtjs/supabase`

**API communication:** Raw `fetch()` in `<script setup>` blocks using `useRuntimeConfig().public.apiUrl`. No composable wrapper, no Pinia store for API state (MVP simplicity).

**Page routing:** File-based (`pages/` directory auto-creates routes):

| File | Route | Description |
|------|-------|-------------|
| `pages/index.vue` | `/` | Home / duplicate of dashboard |
| `pages/dashboard.vue` | `/dashboard` | Stats + recent audits table |
| `pages/analyze.vue` | `/analyze` | URL input + polling + score cards |
| `pages/brand-voice.vue` | `/brand-voice` | Brand voice checker UI |
| `pages/optimization.vue` | `/optimization` | Recommendations (placeholder) |
| `pages/settings.vue` | `/settings` | Settings page |
| `pages/login.vue` | `/login` | Login form |

**Layout:** Single layout `layouts/dashboard.vue` wraps all authenticated pages via `<NuxtLayout name="dashboard">`.

**Polling pattern (analyze.vue):**
```javascript
// POST to /analyze → get analysis_id
// setInterval 2s → GET /{analysis_id}
// Stop when status === "completed" or "failed" or after 30 attempts (60s timeout)
```

---

## 10. Configuration and Secrets

All backend configuration is managed via `pydantic-settings` (`BaseSettings`) in `backend/app/core/config.py`. The `settings` singleton is imported everywhere.

Key environment variables:

| Variable | Required | Purpose |
|----------|----------|---------|
| `SECRET_KEY` | Yes | JWT signing key (32 hex chars) |
| `DATABASE_URL` | Yes | PostgreSQL DSN |
| `SUPABASE_URL` | Yes | Supabase project URL |
| `SUPABASE_KEY` | Yes | Supabase anon key |
| `OPENAI_API_KEY` | Yes | Embeddings + LLM calls |
| `REDIS_URL` | No | Redis DSN (default: redis://localhost:6379/0) |
| `STRIPE_SECRET_KEY` | No | Payments (stub) |
| `JIRA_BASE_URL` | No | Jira integration (stub) |
| `ENVIRONMENT` | No | `development` or `production` (controls error verbosity) |

Frontend env (in `frontend/.env`):

| Variable | Purpose |
|----------|---------|
| `NUXT_PUBLIC_API_URL` | Backend base URL (exposed to browser) |
| `NUXT_PUBLIC_SUPABASE_URL` | Supabase for client-side auth |
| `NUXT_PUBLIC_SUPABASE_KEY` | Supabase anon key |

---

## 11. Key Abstractions

| Abstraction | Where | Purpose |
|-------------|-------|---------|
| `SecureBaseModel` | `core/validators.py` | All Pydantic request models. Blocks extra fields, validates on assignment. |
| `BaseMeasurement` (OLD) | `geo_data_points/scripts/base_measurement.py` | Sync measurement contract for orchestrator |
| `BaseMeasurement` (NEW) | `geo_data_points/base.py` | Async measurement contract for measurements/ scripts |
| `RateLimiter` | `core/rate_limiter.py` | Redis sliding-window per-IP or per-endpoint counters |
| `GeoOrchestrator` | `geo_data_points/orchestrator/run_all.py` | Runs all OLD scripts sequentially, stores results |
| `AnalyzerService` | `services/analyzer.py` | MVP scoring: crawl + Flesch-Kincaid + keyword matching |
| `BrandVoiceService` | `services/brand_voice.py` | Embedding generation + pgvector cosine similarity + rules |
| `get_db()` | `core/database.py` | SQLAlchemy session dependency (FastAPI `Depends()`) |
| `Settings` | `core/config.py` | Single source of truth for all env vars |
