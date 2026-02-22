# External Integrations

> Generated: 2026-02-21. Sources: `backend/app/api/integrations.py`, `backend/app/services/jira_service.py`, `backend/app/services/optimizer.py`, `backend/app/services/brand_voice.py`, `backend/app/core/config.py`, `geo_data_points/utils/external_apis.py`, `.env.example`, `docker-compose.yml`.

---

## Overview

| Integration | Type | Status | Env Var(s) |
|-------------|------|--------|-----------|
| OpenAI API | LLM + Embeddings | Partially working | `OPENAI_API_KEY` |
| Supabase | Auth + Hosted DB | Wired but redirect disabled | `SUPABASE_URL`, `SUPABASE_KEY` |
| PostgreSQL | Primary database | Working | `DATABASE_URL` |
| Redis | Cache + task broker | Working | `REDIS_URL` |
| Stripe | Payments | Stub (endpoints exist, untested) | `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` |
| Jira | Task management | Stub (mock fallback active) | `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN` |
| Anthropic | LLM (alternative) | Config only, unused in code | `ANTHROPIC_API_KEY` |
| Google PageSpeed Insights | Web performance | Conditional (disabled by default) | `GOOGLE_PAGESPEED_API_KEY` |
| Ahrefs | SEO data | Config only, unused | `AHREFS_API_KEY` |
| SEMrush | SEO data | Config only, unused | `SEMRUSH_API_KEY` |
| Wikidata API | Brand visibility | Active in measurement scripts | none required |
| Wikipedia API | Brand visibility | Active in measurement scripts | none required |
| Google Knowledge Graph | Brand visibility | Conditional | `GOOGLE_PAGESPEED_API_KEY` (reused) |
| Reddit API | Brand visibility | Active in measurement scripts | none required |
| Common Crawl | Content indexing | Active in measurement scripts | none required |
| Sentry | Error monitoring | Config only, not wired | `SENTRY_DSN` |

---

## 1. OpenAI API

**What it is used for:**
- Generating GEO optimization recommendations (chat completions, `gpt-4o-mini`)
- Generating optimized content drafts (chat completions, `gpt-4o-mini`)
- Creating vector embeddings for the Brand Signature Engine (`text-embedding-3-small`, 1536 dims)

**Files that use it:**

| File | Usage |
|------|-------|
| `backend/app/services/optimizer.py` | `openai.chat.completions.create()` — generates recommendations and content optimization |
| `backend/app/services/brand_voice.py` | `openai.embeddings.create()` — generates 1536-dim embeddings for brand corpus chunks |
| `backend/app/core/config.py` | Declares `OPENAI_API_KEY: str` (required field, no default) |
| `.env.example` | `OPENAI_API_KEY=sk-your_openai_api_key_here` |
| `docker-compose.yml` | Injected as env var into `backend` and `celery` containers |

**Current status:**

- **Brand Voice embeddings:** Working. `BrandVoiceService._generate_embedding()` calls `openai.embeddings.create(model="text-embedding-3-small")` and stores the 1536-dim vector in `voice_vectors.embedding` (pgvector column). Falls back to a zero vector on error.
- **Recommendations:** The `OptimizerService.generate_recommendations()` makes a real OpenAI call with `gpt-4o-mini`. However, the optimization API endpoint (`POST /api/v1/optimization/generate`) is declared but the integration between the analysis pipeline and the optimizer is incomplete — the optimizer is not called automatically after an analysis completes.
- **Fallback:** `_create_fallback_recommendations()` creates three hardcoded stub recommendations if the OpenAI call fails.

**Configuration:**
```python
# backend/app/services/optimizer.py and brand_voice.py
openai.api_key = settings.OPENAI_API_KEY
```

**Model in use:**

| Purpose | Model |
|---------|-------|
| Recommendations | `gpt-4o-mini` |
| Content optimization | `gpt-4o-mini` |
| Embeddings | `text-embedding-3-small` |

---

## 2. Supabase

**What it is used for:**
- Auth provider (user sign-in, session management) — wired in frontend via `@nuxtjs/supabase`
- Originally intended as hosted PostgreSQL replacement; currently the app uses a separate direct PostgreSQL connection for all data operations

**Files that use it:**

| File | Usage |
|------|-------|
| `frontend/nuxt.config.ts` | Module `@nuxtjs/supabase` registered; `redirect: false` set (auth redirect disabled) |
| `frontend/package.json` | `@nuxtjs/supabase: ^1.1.6` dependency |
| `backend/app/core/config.py` | Declares `SUPABASE_URL: str`, `SUPABASE_KEY: str`, `SUPABASE_SERVICE_KEY: str` |
| `docker-compose.yml` | `SUPABASE_URL` and `SUPABASE_KEY` injected into backend and frontend containers |
| `backend/requirements.txt` | `supabase==2.3.0`, `postgrest-py==0.13.0` |
| `.env.example` | `SUPABASE_URL=https://your-project.supabase.co`, `SUPABASE_KEY=your-anon-key-here` |

**Current status:**

- **Frontend:** Supabase module is loaded and configured. Auth redirect is explicitly disabled (`redirect: false`) so all pages are accessible without login. The module is present but not actively gating any routes.
- **Backend:** The Python `supabase` client library is installed (`2.24.0` in venv) and the config values are declared as required fields, but no backend service file directly imports or instantiates the Supabase client. All database operations go through SQLAlchemy directly to the local PostgreSQL instance.
- **Overall:** Wired at the infra level; auth is disabled for MVP; the Supabase backend client is installed but not actively called.

---

## 3. PostgreSQL (via pgvector image)

**What it is used for:**
- Primary relational data store for all application data
- Vector similarity search for Brand Signature Engine (pgvector extension)

**Files that use it:**

| File | Usage |
|------|-------|
| `backend/app/core/database.py` | SQLAlchemy engine creation, `SessionLocal` factory, `get_db()` dependency |
| `backend/app/models/analysis.py` | `analyses` table |
| `backend/app/models/organization.py` | `organizations` table |
| `backend/app/models/profile.py` | `profiles` table |
| `backend/app/models/website.py` | `websites` table |
| `backend/app/models/recommendation.py` | `recommendations` table |
| `backend/app/models/brand_voice.py` | `brand_voice_configs`, `voice_vectors` (pgvector `Vector(1536)`), `voice_rules` tables |
| `backend/app/services/brand_voice.py` | Raw SQL `<=>` cosine distance operator for similarity search |
| `docker-compose.yml` | `ankane/pgvector:latest` image; volume `postgres_data` |
| `geo_data_points/db/` | Separate SQLite/PostgreSQL connection for measurement results |

**Current status:** Working. The pgvector extension is provided by the `ankane/pgvector` Docker image. The `voice_vectors` table uses `Column(Vector(1536))` from `pgvector.sqlalchemy`. Cosine similarity queries use the `<=>` operator directly in raw SQL within `BrandVoiceService._calculate_vector_similarity()`.

**Connection pool:**
- `pool_size=10`, `max_overflow=20`, `pool_pre_ping=True`

**Docker:**
```yaml
image: ankane/pgvector:latest
ports: ["5432:5432"]
```

---

## 4. Redis

**What it is used for:**
- Celery message broker (task queue for background analysis jobs)
- Rate limiter backend (sliding window counters, per IP/user/endpoint/global)

**Files that use it:**

| File | Usage |
|------|-------|
| `backend/app/core/rate_limiter.py` | `redis.Redis.from_url(settings.REDIS_URL)` — stores window counters with `setex` / `incr` |
| `docker-compose.yml` | `redis:7-alpine` image; volume `redis_data`; injected as `REDIS_URL` |
| `backend/app/core/config.py` | `REDIS_URL: str = "redis://localhost:6379/0"` (has default) |

**Current status:** Working. Redis is used by the rate limiter on every API request. The rate limiter gracefully degrades (fails open) if Redis is unavailable — an error is logged but the request is not blocked. Celery broker configuration references `REDIS_URL` via `docker-compose.yml` but Celery task module (`app.tasks.celery_app`) is not present in the explored source files — the worker is declared in docker-compose but the task module is likely incomplete.

**Rate limit tiers enforced via Redis:**

| Limiter | Limit | Window |
|---------|-------|--------|
| `standard_rate_limit` | 100 req | 60 s |
| `strict_rate_limit` | 10 req | 60 s |
| `analysis_rate_limit` | 3 req | 300 s |
| `optimization_rate_limit` | 10 req | 60 s |
| `upload_rate_limit` | 5 req | 3600 s |
| `integration_rate_limit` | 20 req | 60 s |

---

## 5. Stripe

**What it is used for:**
- Subscription checkout session creation (pro / enterprise tiers)
- Webhook handling for `checkout.session.completed` and `customer.subscription.deleted` events
- Updating `organizations.subscription_tier` and `organizations.stripe_customer_id` on payment

**Files that use it:**

| File | Usage |
|------|-------|
| `backend/app/api/integrations.py` | `stripe.checkout.Session.create()`, `stripe.Webhook.construct_event()`, `stripe.error.StripeError`, `stripe.error.SignatureVerificationError` |
| `backend/app/models/organization.py` | `stripe_customer_id` column on `Organization` |
| `backend/requirements.txt` | `stripe==7.9.0` |
| `backend/app/core/config.py` | `STRIPE_SECRET_KEY: str = ""`, `STRIPE_WEBHOOK_SECRET: str = ""` |
| `docker-compose.yml` | `STRIPE_SECRET_KEY` injected into backend container |
| `.env.example` | `STRIPE_SECRET_KEY=your_stripe_secret_key_here` |

**API endpoints exposed:**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/integrations/stripe/create-checkout` | POST | Create checkout session for org |
| `/api/v1/integrations/stripe/webhook` | POST | Receive Stripe webhook events |

**Current status:** **Stub — endpoints exist, untested.** The price IDs are hardcoded placeholder strings (`"price_pro_monthly"`, `"price_enterprise_monthly"`) that do not correspond to real Stripe products. The webhook secret validation logic is correct (HMAC verification via `stripe.Webhook.construct_event`), but `STRIPE_WEBHOOK_SECRET` is empty by default. Authentication on the checkout endpoint is commented out. The code is structurally complete; it needs real Stripe product/price IDs and credentials to function.

---

## 6. Jira

**What it is used for:**
- Creating Jira tickets from GEO optimization recommendations
- Linking tickets back to `recommendations.jira_ticket_id` in the database

**Files that use it:**

| File | Usage |
|------|-------|
| `backend/app/services/jira_service.py` | `JiraService` class — `requests.post()` to Jira REST API v3 (`/rest/api/3/issue`) with `HTTPBasicAuth` |
| `backend/app/api/integrations.py` | Instantiates `JiraService`, calls `create_ticket()`, stores ticket key |
| `backend/app/core/config.py` | `JIRA_BASE_URL: str = ""`, `JIRA_EMAIL: str = ""`, `JIRA_API_TOKEN: str = ""` |
| `.env.example` | `JIRA_BASE_URL=https://your-domain.atlassian.net`, `JIRA_API_TOKEN=your_jira_api_token_here` |

**API endpoint exposed:**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/integrations/jira/create-ticket` | POST | Create Jira task from recommendation |

**Current status:** **Stub with mock fallback.** `JiraService.__init__()` checks if all three credentials (`base_url`, `email`, `api_token`) are set. If any is missing, it prints a warning and operates in mock mode. `create_ticket()` returns `f"MOCK-{project_key}-123"` when unconfigured, and `f"ERROR-{project_key}-000"` on API failures. The REST API payload uses Atlassian Document Format (ADF) for the description body. The endpoint requires a `recommendation_id` (UUID) that points to an existing recommendation — since recommendations require a completed analysis and working optimizer, this integration is functionally blocked until the recommendation pipeline is wired.

---

## 7. Anthropic API

**What it is used for:**
- Declared as an optional alternative LLM provider
- Listed in `.env.example` under "External APIs (optional)"

**Files that use it:**

| File | Usage |
|------|-------|
| `backend/app/core/config.py` | `ANTHROPIC_API_KEY: str = ""` (optional, empty default) |
| `geo_data_points/utils/config.py` | `self.ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")` |
| `.env.example` | `ANTHROPIC_API_KEY=sk-ant-your_anthropic_key_here` |

**Current status:** **Config only — not used in any service.** The key is loaded but no file imports the `anthropic` Python SDK or calls any Anthropic endpoint. LiteLLM (which is installed) supports Anthropic models, so this could be activated through LiteLLM without code changes if the key is configured.

---

## 8. Google PageSpeed Insights API

**What it is used for:**
- Measuring Core Web Vitals (LCP, FID, CLS) for UX scoring in the 108-point system
- Powering the `wi_page_speed_insights.py` and `ux_core_web_vitals_lcp.py` measurement scripts

**Files that use it:**

| File | Usage |
|------|-------|
| `geo_data_points/utils/external_apis.py` | `PageSpeedClient` class — `GET https://www.googleapis.com/pagespeedonline/v5/runPagespeed` with `GOOGLE_PAGESPEED_API_KEY` |
| `geo_data_points/utils/config.py` | `self.GOOGLE_PAGESPEED_API_KEY = os.getenv("GOOGLE_PAGESPEED_API_KEY", "")` |
| `.env.example` | `GOOGLE_PAGESPEED_API_KEY=your_google_pagespeed_key_here` |

**Current status:** **Conditional — disabled by default.** The `GeoConfig.ENABLE_EXTERNAL_APIS` flag defaults to `false` (`GEO_ENABLE_EXTERNAL_APIS=false`). `PageSpeedClient.analyze_url()` returns `None` and logs a warning if `GOOGLE_PAGESPEED_API_KEY` is not set. The rate limiter is set to 25 calls/minute. Results are cached via `@lru_cache(maxsize=100)`. The `GoogleKnowledgeGraphClient` also reuses this same API key.

---

## 9. Ahrefs API

**What it is used for:**
- Intended for backlink data and domain authority scoring (`seo_backlinks_count.py`, `seo_domain_authority.py`)

**Files that use it:**

| File | Usage |
|------|-------|
| `geo_data_points/utils/config.py` | `self.AHREFS_API_KEY = os.getenv("AHREFS_API_KEY", "")` |
| `.env.example` | `AHREFS_API_KEY=your_ahrefs_key_here` |

**Current status:** **Config only — not wired.** The key is loaded in `GeoConfig` but `geo_data_points/utils/external_apis.py` has no `AhrefsClient` implementation. The measurement scripts that would use it (`seo_backlinks_count.py`, `seo_domain_authority.py`) likely return 0 scores.

---

## 10. SEMrush API

**What it is used for:**
- Intended for keyword rankings, organic traffic, and competitive data

**Files that use it:**

| File | Usage |
|------|-------|
| `geo_data_points/utils/config.py` | `self.SEMRUSH_API_KEY = os.getenv("SEMRUSH_API_KEY", "")` |
| `.env.example` | `SEMRUSH_API_KEY=your_semrush_key_here` |

**Current status:** **Config only — not implemented.** No client class exists for SEMrush in `external_apis.py`.

---

## 11. Wikidata API (Public)

**What it is used for:**
- Checking brand entity presence on Wikidata (QID lookup)
- Used in `bv_wikidata_qid.py` measurement

**Files that use it:**

| File | Usage |
|------|-------|
| `geo_data_points/utils/external_apis.py` | `WikidataClient` class — `GET https://www.wikidata.org/w/api.php` with `wbsearchentities` and `wbgetentities` actions |

**Current status:** **Active — no API key required.** Rate limit: 200 calls/minute (self-enforced). Results cached via `@lru_cache(maxsize=1000)`.

---

## 12. Wikipedia API (Public)

**What it is used for:**
- Checking brand Wikipedia page existence (`bv_wikipedia_presence.py`)
- Counting Wikipedia backlinks to a domain

**Files that use it:**

| File | Usage |
|------|-------|
| `geo_data_points/utils/external_apis.py` | `WikipediaClient` class — `GET https://en.wikipedia.org/w/api.php` with `opensearch` and `exturlusage` query actions |

**Current status:** **Active — no API key required.** Rate limit: 200 calls/minute (self-enforced). Results cached via `@lru_cache(maxsize=1000)`.

---

## 13. Google Knowledge Graph Search API

**What it is used for:**
- Checking brand entity presence in Google's Knowledge Graph
- Used in `bv_knowledge_graph_presence.py` measurement

**Files that use it:**

| File | Usage |
|------|-------|
| `geo_data_points/utils/external_apis.py` | `GoogleKnowledgeGraphClient` class — `GET https://kgsearch.googleapis.com/v1/entities:search` |

**Current status:** **Conditional — requires `GOOGLE_PAGESPEED_API_KEY`.** Returns `None` and logs a warning if no key. The same Google API key used for PageSpeed is reused here (both are Google APIs enabled per GCP project). Rate limit: 100 calls/minute. Results cached via `@lru_cache(maxsize=1000)`.

---

## 14. Reddit API (Public Read-Only)

**What it is used for:**
- Counting brand mentions on Reddit (`bv_brand_mentions.py`, `bv_social_engagement.py` context)

**Files that use it:**

| File | Usage |
|------|-------|
| `geo_data_points/utils/external_apis.py` | `RedditClient` class — `GET https://www.reddit.com/search.json` with `User-Agent: GEO-Platform-Bot/1.0` |

**Current status:** **Active — no API key required** (uses public JSON search endpoint). Rate limit: 60 calls/minute (self-enforced). Results cached via `@lru_cache(maxsize=100)`. Note: Reddit's public API has rate limits and may require authentication for sustained use.

---

## 15. Common Crawl Index API (Public)

**What it is used for:**
- Estimating domain page count from Common Crawl index data (`cnt_content_depth_score.py` context)

**Files that use it:**

| File | Usage |
|------|-------|
| `geo_data_points/utils/external_apis.py` | `CommonCrawlClient` class — `GET https://index.commoncrawl.org/CC-MAIN-2024-10-index` |

**Current status:** **Active — no API key required.** Rate limit: 30 calls/minute (self-enforced). Results cached via `@lru_cache(maxsize=100)`. The index URL is hardcoded to the `CC-MAIN-2024-10` crawl snapshot.

---

## 16. Sentry

**What it is used for:**
- Error monitoring and alerting

**Files that use it:**

| File | Usage |
|------|-------|
| `backend/requirements.txt` | `sentry-sdk==1.39.0` |
| `backend/app/core/config.py` | `SENTRY_DSN: str = ""` (optional, empty default) |
| `.env.example` | Not listed (omitted from template) |

**Current status:** **Not wired.** The `sentry-sdk` package is installed (`2.47.0` in venv) and the DSN is configurable, but `sentry_sdk.init()` is never called in `backend/app/main.py` or any other module. Sentry integration is a zero-effort add once a DSN is available.

---

## Integration Dependency Map

```
URL Analysis Request
  └── AnalyzerService.run_analysis()
        ├── requests.get(url)          ← direct HTTP, no API key
        ├── BeautifulSoup              ← local parsing
        ├── textstat                   ← local scoring
        └── (planned) Playwright      ← local headless browser

GEO Data Points Analysis
  └── GeoOrchestrator.run_all()
        ├── wi_*.py, cnt_*.py, seo_*.py, ux_*.py, leg_*.py
        │     ├── requests.get()       ← direct HTTP crawl
        │     ├── BeautifulSoup        ← local parsing
        │     └── PageSpeedClient      ← Google API (disabled by default)
        └── bv_*.py, comp_*.py
              ├── WikidataClient       ← Wikidata (free)
              ├── WikipediaClient      ← Wikipedia (free)
              ├── GoogleKnowledgeGraphClient ← Google API (key required)
              ├── RedditClient         ← Reddit (free, no key)
              └── CommonCrawlClient    ← Common Crawl (free)

Brand Voice Check
  └── BrandVoiceService.check_voice()
        ├── _generate_embedding()     ← OpenAI embeddings API (REQUIRED)
        └── pgvector <=> query        ← PostgreSQL (local)

Recommendations Generation
  └── OptimizerService.generate_recommendations()
        └── openai.chat.completions   ← OpenAI Chat API (REQUIRED)

Stripe Checkout
  └── stripe.checkout.Session.create() ← Stripe API
  └── stripe.Webhook.construct_event() ← HMAC verification

Jira Ticket
  └── JiraService.create_ticket()
        └── requests.post(JIRA_BASE_URL/rest/api/3/issue) ← Jira REST API
```

---

## Required vs Optional by Feature

| Feature | Required | Optional |
|---------|----------|---------|
| URL analysis (basic scoring) | PostgreSQL, Redis | — |
| GEO data points (103 remaining scripts) | PostgreSQL | Google PageSpeed, Ahrefs, SEMrush |
| Brand Voice (layers 1 + 3) | PostgreSQL + pgvector, **OpenAI** | — |
| Brand Voice (layer 4 LLM deep analysis) | **OpenAI** (or LiteLLM alternative) | Anthropic |
| Recommendations | **OpenAI** | — |
| Authentication | Supabase (frontend) | — |
| Payments | **Stripe** | — |
| Jira tickets | **Jira credentials** | — |
| Error monitoring | — | Sentry |
| Brand visibility measurements | — | Wikidata, Wikipedia, Reddit, Common Crawl, Google KG |
