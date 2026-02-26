# Directory Structure — GEO Platform MVP

> Generated: 2026-02-21. Maps every directory and key file. Use this as the reference for where new files go.

---

## Complete Directory Tree

```
geo-platform-mvp/                          # Project root
├── CLAUDE.md                              # Project guide (read first)
├── README.md                              # Public intro
├── docker-compose.yml                     # 5-service orchestration
├── .env.example                           # Root env template
├── .gitignore
├── data_points.json                       # 108 data point definitions (root copy)
├── test_all_measurements.py               # Standalone test for measurements/
│
├── .planning/                             # Agent planning artifacts
│   └── codebase/
│       ├── ARCHITECTURE.md               # This project's arch doc
│       └── STRUCTURE.md                  # This file
│
├── .claude/                               # Claude Code config + skills
│   ├── settings.json
│   └── skills/
│       └── ui-ux-pro-max/                # UI design intelligence skill
│
├── docs/                                  # Human-authored project docs
│   ├── quickstart-your-claude.md         # Workflow guide for AI sessions
│   ├── BACKLOG.md                        # Prioritized task list
│   ├── progression.md                    # Changelog / task tracking
│   ├── CONNECTIONS.md                    # External service map
│   ├── DEPLOYMENTS.md                    # Deployment log
│   ├── INCIDENTS.md                      # Known errors + fixes
│   ├── ARCHITECTURE.md                   # Human-written arch notes
│   ├── GEO-DATA-POINTS.md               # 108-measurement system docs
│   ├── API-REFERENCE.md                  # All API endpoints
│   ├── TESTING-STRATEGY.md              # Testing tiers
│   ├── SECURITY.md                       # Security implementation
│   └── archive/                          # Historical docs
│
├── design-system/
│   └── endexa-geo-platform/
│       └── MASTER.md                     # Design tokens: colors, fonts, style
│
├── backend/                               # FastAPI Python application
│   ├── Dockerfile
│   ├── requirements.txt                   # Python dependencies
│   ├── .env                              # Backend secrets (git-ignored)
│   ├── .env.example                      # Template
│   ├── RAG_SYSTEM_README.md
│   ├── logs/
│   │   └── app.log                       # Loguru log file (rotation 500MB)
│   ├── scripts/
│   │   └── init_rag_system.py            # One-time RAG init script
│   └── app/                              # Application package
│       ├── main.py                       # FastAPI app + middleware stack + router registration
│       ├── api/                          # HTTP route handlers
│       │   ├── __init__.py
│       │   ├── analysis.py               # POST /analyze, GET /{id}, GET /{id}/recommendations
│       │   ├── brand_voice.py            # POST /config, upload, rule, check; GET /config/{id}
│       │   ├── dashboard.py              # GET /stats, GET /history
│       │   ├── geo_datapoints.py         # POST /run, GET /{id}, /summary, /module/{m}
│       │   ├── integrations.py           # Jira tickets, Stripe checkout + webhook
│       │   └── optimization.py           # POST /generate, /optimize-content, PATCH /{id}/implement
│       ├── core/                         # Infrastructure and cross-cutting concerns
│       │   ├── config.py                 # pydantic-settings Settings class (all env vars)
│       │   ├── database.py               # SQLAlchemy engine + SessionLocal + get_db()
│       │   ├── middleware.py             # 8 custom ASGI middlewares
│       │   ├── rate_limiter.py           # Redis-backed rate limiters + pre-configured instances
│       │   ├── security.py               # JWT, bcrypt, API key, RBAC, OrganizationChecker
│       │   └── validators.py             # URLValidator, StringSanitizer, SecureBaseModel, etc.
│       ├── models/                       # SQLAlchemy ORM models (DB schema)
│       │   ├── __init__.py               # Exports all models for easy import
│       │   ├── analysis.py               # Analysis table
│       │   ├── brand_voice.py            # BrandVoiceConfig, VoiceVector (pgvector), VoiceRule
│       │   ├── organization.py           # Organization table
│       │   ├── profile.py                # Profile table (links to Supabase auth)
│       │   ├── recommendation.py         # Recommendation table
│       │   └── website.py                # Website table
│       ├── services/                     # Business logic layer
│       │   ├── __init__.py
│       │   ├── analyzer.py               # AnalyzerService: crawl + scoring pipeline
│       │   ├── brand_voice.py            # BrandVoiceService: chunking + embeddings + rules
│       │   ├── jira_service.py           # JiraService: ticket creation via Jira REST API
│       │   └── optimizer.py              # OptimizerService: recommendation generation (stub)
│       └── tasks/                        # Celery task definitions
│           └── (empty / not yet wired)   # celery_app referenced in docker-compose
│
├── frontend/                              # Nuxt 3 frontend application
│   ├── Dockerfile
│   ├── package.json
│   ├── nuxt.config.ts                    # Nuxt config: modules, runtimeConfig, head
│   ├── tailwind.config.js                # Tailwind: colors, fonts, extensions
│   ├── .env                              # Frontend secrets (git-ignored)
│   ├── .env.example
│   ├── app.vue                           # Root Vue component
│   ├── assets/
│   │   └── css/
│   │       └── main.css                  # Tailwind directives + global styles
│   ├── public/                           # Static assets
│   ├── layouts/
│   │   └── dashboard.vue                 # Sidebar + nav layout wrapping all pages
│   ├── pages/                            # File-based routing (auto-configured)
│   │   ├── index.vue                     # Route: /  (home/dashboard duplicate)
│   │   ├── analyze.vue                   # Route: /analyze (core feature)
│   │   ├── dashboard.vue                 # Route: /dashboard
│   │   ├── brand-voice.vue               # Route: /brand-voice
│   │   ├── optimization.vue              # Route: /optimization
│   │   ├── settings.vue                  # Route: /settings
│   │   └── login.vue                     # Route: /login
│   ├── components/                       # Reusable Vue components (empty currently)
│   └── composables/                      # Vue composables / hooks (empty currently)
│
└── geo_data_points/                       # GEO measurement scripts module
    ├── __init__.py
    ├── base.py                           # NEW BaseMeasurement (async, with code/name/weight)
    ├── data_points.json                  # 108 data point definitions
    ├── init_db.py                        # Standalone DB init script
    ├── requirements.txt                  # geo_data_points-specific deps
    ├── test_measurements.py              # Module-level unit tests
    ├── README.md
    ├── QUICK_START.md
    ├── IMPLEMENTATION_SUMMARY.md
    │
    ├── db/                               # geo_data_points own DB layer
    │   ├── __init__.py                   # Exports: Analysis, DataPointResult, get_db_session, etc.
    │   ├── models.py                     # geo_analyses + geo_data_point_results tables
    │   └── database.py                   # SQLAlchemy engine for geo_data_points DB
    │
    ├── orchestrator/                     # OLD system: runs scripts/
    │   ├── __init__.py
    │   └── run_all.py                    # GeoOrchestrator class: loads JSON, runs scripts/, stores to DB
    │
    ├── scripts/                          # OLD measurement scripts (5 total) — CONNECTED to orchestrator
    │   ├── __init__.py
    │   ├── base_measurement.py           # OLD BaseMeasurement (sync, takes url in __init__)
    │   ├── robots_txt_gptbot.py          # class RobotsTxtGPTBot
    │   ├── robots_txt_claudebot.py       # class RobotsTxtClaudebot
    │   ├── schema_org_organization.py    # class SchemaOrgOrganization
    │   ├── response_time.py              # class ResponseTime
    │   └── title_tag_optimization.py     # class TitleTagOptimization
    │
    ├── measurements/                     # NEW measurement scripts (99 total) — NOT CONNECTED
    │   ├── base_measurement.py           # Simple async BaseMeasurement (minimal)
    │   ├── wi_*.py  (26 files)           # Web Infrastructure
    │   ├── cnt_*.py (21 files)           # Content
    │   ├── bv_*.py  (15 files)           # Brand Visibility
    │   ├── seo_*.py (12 files)           # SEO
    │   ├── ux_*.py  (8 files)            # UX
    │   ├── comp_*.py (8 files)           # Competitive
    │   └── leg_*.py (5 files)            # Legal
    │
    ├── utils/                            # Shared utilities for measurement scripts
    │   ├── __init__.py                   # Exports: get_logger, get_config, validate_url, normalize_url
    │   ├── config.py                     # Config dataclass: DB_URL, DATA_POINTS_JSON path, timeouts
    │   ├── logging.py                    # Loguru-based GeoLogger with measurement_start/complete/error
    │   ├── helpers.py                    # get_base_url(), normalize_url(), validate_url()
    │   ├── http_client.py                # CachedSession: requests wrapper with caching + retry
    │   ├── html_parser.py                # BeautifulSoup wrappers, heading extraction, schema parsing
    │   ├── content_analyzer.py           # Text analysis: readability, entity density, sentiment
    │   ├── seo_helpers.py                # robots.txt parser, sitemap reader, canonical URL checker
    │   ├── crawl_helpers.py              # Crawl utilities, response time measurement
    │   └── external_apis.py              # Wrappers for external APIs (PageSpeed, Wikidata, etc.)
    │
    └── logs/                             # geo_data_points log files
        └── geo_platform.log
```

---

## Key File Locations

### Entry Points

| Purpose | File |
|---------|------|
| FastAPI application | `/home/salim/Informatique/Perso/Endexa/geo-platform-mvp/backend/app/main.py` |
| Uvicorn command | `uvicorn app.main:app --host 0.0.0.0 --port 8000` |
| Celery worker | `celery -A app.tasks.celery_app worker` |
| Nuxt dev server | `npm run dev` from `frontend/` |
| GEO orchestrator (standalone) | `python geo_data_points/orchestrator/run_all.py <url>` |
| DB init (geo_data_points) | `python geo_data_points/init_db.py` |

### Configuration Files

| Purpose | File |
|---------|------|
| Backend settings | `/home/salim/Informatique/Perso/Endexa/geo-platform-mvp/backend/app/core/config.py` |
| Backend env vars | `/home/salim/Informatique/Perso/Endexa/geo-platform-mvp/backend/.env` |
| Frontend config | `/home/salim/Informatique/Perso/Endexa/geo-platform-mvp/frontend/nuxt.config.ts` |
| Frontend env vars | `/home/salim/Informatique/Perso/Endexa/geo-platform-mvp/frontend/.env` |
| Docker services | `/home/salim/Informatique/Perso/Endexa/geo-platform-mvp/docker-compose.yml` |
| Python deps | `/home/salim/Informatique/Perso/Endexa/geo-platform-mvp/backend/requirements.txt` |
| JS deps | `/home/salim/Informatique/Perso/Endexa/geo-platform-mvp/frontend/package.json` |
| Tailwind config | `/home/salim/Informatique/Perso/Endexa/geo-platform-mvp/frontend/tailwind.config.js` |

---

## Naming Conventions

### Backend (Python)

| Entity | Convention | Example |
|--------|-----------|---------|
| API router files | `snake_case.py` | `brand_voice.py`, `geo_datapoints.py` |
| Service files | `snake_case.py` (noun) | `analyzer.py`, `brand_voice.py` |
| Model files | `snake_case.py` (noun) | `analysis.py`, `organization.py` |
| SQLAlchemy table names | `snake_case` plural | `analyses`, `voice_vectors`, `geo_analyses` |
| Pydantic request models | `PascalCaseRequest` | `AnalyzeRequest`, `CreateConfigRequest` |
| Pydantic response models | `PascalCaseResponse` | `AnalysisResponse` |
| Secure request models | `SecurePascalCaseRequest` | `SecureAnalyzeRequest`, `SecureJiraRequest` |
| Route handler functions | `snake_case` verb-noun | `create_analysis`, `get_geo_analysis_summary` |
| Service methods | `snake_case` verb-noun | `run_analysis`, `process_knowledge_base` |
| Core utilities | `snake_case` noun | `rate_limiter.py`, `validators.py` |

### OLD measurements (scripts/)

| Entity | Convention | Example |
|--------|-----------|---------|
| Script file | `snake_case.py` (topic) | `robots_txt_gptbot.py` |
| Class name | `PascalCase` derived from filename | `RobotsTxtGPTBot` |
| Method | `measure(self) -> Dict` | synchronous, no args |

### NEW measurements (measurements/)

| Entity | Convention | Example |
|--------|-----------|---------|
| Script file | `{prefix}_{topic}.py` | `wi_robots_txt_bingbot.py` |
| Module prefix | 2–4 char category code | `wi_`, `cnt_`, `bv_`, `seo_`, `ux_`, `comp_`, `leg_` |
| Class name | `PascalCaseMeasurement` | `RobotsTxtBingbotMeasurement` |
| Constructor | `__init__(self)` calling `super().__init__(code, name, description, category, weight)` | |
| Method | `async measure(self, url, html, metadata) -> Dict` | |
| Module export | `measurement = XyzMeasurement()` (singleton) | `measurement = RobotsTxtBingbotMeasurement()` |
| Measurement codes | `{MODULE}-{NNN}` | `WI-009`, `CNT-003`, `BV-001` |

### Frontend (Vue / Nuxt)

| Entity | Convention | Example |
|--------|-----------|---------|
| Page files | `kebab-case.vue` | `brand-voice.vue`, `analyze.vue` |
| Component files | `PascalCase.vue` (when added) | `ScoreCard.vue`, `NavSidebar.vue` |
| Composable files | `use-kebab-case.ts` | `use-api.ts` |
| CSS classes | Tailwind utilities + design system tokens | `btn-primary`, `card`, `input-field` |
| Reactive state | `ref()` and `computed()` in `<script setup>` | `const analyzing = ref(false)` |

---

## Where New Files Go

### Adding a new API route

1. Create `backend/app/api/<feature>.py`
2. Define `router = APIRouter()`
3. Import and register in `backend/app/main.py`:
   ```python
   from app.api import <feature>
   app.include_router(<feature>.router, prefix=f"{settings.API_V1_PREFIX}/<path>", tags=["<tag>"])
   ```

Template:
```python
# backend/app/api/my_feature.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.rate_limiter import standard_rate_limit
from app.core.validators import SecureBaseModel

router = APIRouter()

class MyRequest(SecureBaseModel):
    field: str

@router.post("/action", dependencies=[Depends(standard_rate_limit)])
async def do_action(request: MyRequest, db: Session = Depends(get_db)):
    ...
```

### Adding a new service

Create `backend/app/services/<service_name>.py`. No registration needed — import directly from the router that uses it.

```python
# backend/app/services/my_service.py
from sqlalchemy.orm import Session

class MyService:
    def __init__(self, db: Session):
        self.db = db

    def do_something(self, param: str) -> dict:
        ...
```

### Adding a new SQLAlchemy model

1. Create `backend/app/models/<model_name>.py`
2. Add import to `backend/app/models/__init__.py`
3. `Base.metadata.create_all(bind=engine)` in `main.py` will auto-create the table

```python
# backend/app/models/my_model.py
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.core.database import Base

class MyModel(Base):
    __tablename__ = "my_models"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
```

### Adding a new measurement script (OLD system — connects to orchestrator)

Add to `geo_data_points/scripts/`. The orchestrator discovers scripts by converting the data point name from `data_points.json` to a module name, so the filename must match exactly.

**Naming:** `data_point_name.lower().replace(' - ', '_').replace('.', '_').replace(' ', '_')`

```python
# geo_data_points/scripts/<module_name>.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from scripts.base_measurement import BaseMeasurement
from utils import get_base_url

class MyMeasurementName(BaseMeasurement):
    def measure(self) -> dict:
        return {
            'score': 75.0,
            'comment': 'Explanation of score',
            'metadata': {}
        }
```

### Adding a new measurement script (NEW system — measurements/)

Add to `geo_data_points/measurements/`. These are NOT yet connected to any orchestrator, but follow this pattern for consistency with the existing 99 scripts.

```python
# geo_data_points/measurements/{prefix}_{topic}.py
from typing import Dict, Any
from geo_data_points.base import BaseMeasurement
from geo_data_points.utils.http_client import CachedSession

class MyTopicMeasurement(BaseMeasurement):
    def __init__(self):
        super().__init__(
            code="WI-NNN",          # next sequential code in module
            name="Human Readable Name",
            description="What this measures and why it matters for GEO",
            category="Web Infrastructure",  # or Content / Brand Visibility / SEO / UX / Competitive / Legal
            weight=0.8              # 0.0–1.0, importance relative to module
        )
        self.session = CachedSession()

    async def measure(self, url: str, html: str = None, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        try:
            # ... implementation ...
            return {
                'score': 80,
                'comment': 'Actionable explanation of score'
            }
        except Exception as e:
            return {'score': 0, 'comment': f'Measurement failed: {str(e)}'}

# Required singleton export
measurement = MyTopicMeasurement()
```

### Adding a new frontend page

Create `frontend/pages/<page-name>.vue`. Nuxt auto-creates the route `/page-name`.

```vue
<!-- frontend/pages/my-page.vue -->
<template>
  <NuxtLayout name="dashboard">
    <div class="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 class="text-3xl font-bold text-gray-900">Page Title</h1>
        <p class="text-gray-600 mt-1">Subtitle</p>
      </div>
      <!-- content -->
    </div>
  </NuxtLayout>
</template>

<script setup lang="ts">
const config = useRuntimeConfig()
// State and API calls here
</script>
```

### Adding a new frontend component

Create `frontend/components/<ComponentName>.vue`. Nuxt auto-imports all components — no import statement needed in pages.

```vue
<!-- frontend/components/ScoreCard.vue -->
<template>
  <div class="card">
    <p class="text-sm text-gray-600">{{ label }}</p>
    <p class="text-3xl font-bold mt-2">{{ score }}</p>
  </div>
</template>

<script setup lang="ts">
defineProps<{ label: string; score: number }>()
</script>
```

### Adding a new composable

Create `frontend/composables/use-<name>.ts`. Nuxt auto-imports — no import needed in pages or components.

```typescript
// frontend/composables/use-analysis.ts
export const useAnalysis = () => {
  const config = useRuntimeConfig()
  const loading = ref(false)

  const fetchAnalysis = async (id: string) => {
    loading.value = true
    const data = await $fetch(`${config.public.apiUrl}/api/v1/analysis/${id}`)
    loading.value = false
    return data
  }

  return { loading, fetchAnalysis }
}
```

---

## Module Prefixes (geo_data_points)

| Prefix | Module Name | Count (measurements/) |
|--------|------------|----------------------|
| `wi_` | Web Infrastructure | 26 |
| `cnt_` | Content | 21 |
| `bv_` | Brand Visibility | 15 |
| `seo_` | SEO | 12 |
| `ux_` | UX | 8 |
| `comp_` | Competitive | 8 |
| `leg_` | Legal | 5 |
| — | (base + init) | 2 |
| **Total** | | **~99** |

---

## Critical Paths and Cross-Cutting Files

### Most-edited files for new features

| Task | Files to touch |
|------|---------------|
| New analysis metric | `services/analyzer.py`, `models/analysis.py`, `api/analysis.py` |
| New brand voice layer | `services/brand_voice.py`, `api/brand_voice.py` |
| New GEO measurement (OLD) | `geo_data_points/scripts/<name>.py` |
| New GEO measurement (NEW) | `geo_data_points/measurements/<prefix>_<name>.py` |
| New API endpoint | `api/<feature>.py`, `main.py` (register router) |
| New DB table | `models/<name>.py`, `models/__init__.py` |
| New frontend route | `pages/<name>.vue` |
| New rate limit | `core/rate_limiter.py` (define), `api/<router>.py` (apply) |
| New env variable | `core/config.py` (add field), `.env.example` (document) |

### Files that must stay consistent with each other

- `geo_data_points/data_points.json` and `data_points.json` (root) — same file, two copies; keep in sync
- `geo_data_points/orchestrator/run_all.py` module path format: `"scripts.{module_name}"` must match filenames in `scripts/`
- `backend/app/models/__init__.py` must export every model used in routers
- `docker-compose.yml` env vars must match `backend/app/core/config.py` field names

---

## What Is and Is Not Implemented

### Working (backend wired end-to-end)

- `POST /api/v1/analysis/analyze` → `AnalyzerService` → stores results → frontend polls
- `GET /api/v1/dashboard/stats` → DB aggregation → frontend renders
- `POST /api/v1/voice/config` and `/check` → `BrandVoiceService` → pgvector similarity
- `POST /api/v1/geo-datapoints/run` → `GeoOrchestrator` → 5 real scripts, 103 return 0

### Stubs (endpoint exists, no real implementation)

- `POST /api/v1/optimization/generate` — `OptimizerService` exists, no LLM call wired
- `POST /api/v1/integrations/jira/create-ticket` — `JiraService` exists, endpoint works if `JIRA_API_TOKEN` set
- `POST /api/v1/integrations/stripe/create-checkout` — `stripe.checkout.Session.create()` called, real price IDs missing

### Disabled (code ready, commented out)

- JWT authentication — `get_current_active_user` dependency exists but commented out on all route handlers
- Celery tasks — `celery_app` referenced in docker-compose but `app/tasks/` directory is empty

### Disconnected (code exists, not wired)

- `geo_data_points/measurements/` — 99 async scripts, no orchestrator, no API calls them
- Brand Voice Layer 2 (Statistical Fingerprint) — not built
- Brand Voice Layer 4 (LLM Deep Analysis) — not built
