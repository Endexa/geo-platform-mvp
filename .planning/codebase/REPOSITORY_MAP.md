# GEO Platform MVP - Repository Map

**Analysis Date:** 2026-03-26

---

## Executive Summary

**Architecture Status:** Production-ready infrastructure with modular, well-documented codebase.

**Feature Completeness:** ~60% functional. Core audit pipeline working end-to-end (Phases 1-9). Brand signature partial, payments stubbed.

**Code Quality:** High — consistent patterns, comprehensive middleware stack, Pydantic validation, SQLAlchemy ORM with migrations.

**Technical Debt:** Low. Main gaps are incomplete feature implementations (marked as stubs), not architectural shortcuts.

---

## 1. Architecture Overview

### System Components

```
┌─────────────────┐         ┌─────────────────┐
│  Nuxt 3 SPA     │────────▶│  FastAPI        │
│  (Frontend)     │  REST   │  (Backend)      │
│  Port 3000      │◀────────│  Port 8000      │
└─────────────────┘         └────────┬────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
              ┌─────▼─────┐   ┌─────▼─────┐   ┌─────▼─────┐
              │ Celery    │   │ Redis     │   │ PostgreSQL│
              │ Worker    │   │ (local)   │   │ (Supabase)│
              │ (tasks)   │   │ cache+    │   │ +pgvector │
              └───────────┘   │ broker    │   └───────────┘
                              └───────────┘
```

### Data Flow: Complete Audit Pipeline

**User initiates audit** → POST `/api/v1/audit` → `Audit` record created (status=PENDING)

**Celery task** `run_crawl_and_generate` executes 8 stages:

1. **CRAWLING** — `CrawlerService.crawl()` fetches URL, extracts structured data (title, meta, headings, JSON-LD schemas)
2. **GENERATING_QUERIES** — `QueryGeneratorService` extracts brand name, calls LLM to generate 10-15 queries, stores `AuditQuery` records
3. **DISPATCHING** — `DispatchService` dispatches queries to AI engines (OpenAI, Anthropic, Perplexity, Gemini), creates `EngineResponse` records with raw AI text
4. **ANALYZING** — `MentionDetectorService` scans responses for brand mentions (fuzzy matching), creates `BrandMention` records with char offsets + confidence
5. **SCORING** — `ScoringService` computes visibility score (0-100) using weighted formula: 40% mention rate + 30% position + 30% prominence. Per-engine breakdown + overall score stored in `VisibilityScore`
6. **DISCOVERING_COMPETITORS** — `CompetitorService` extracts named entities from AI responses, creates `DiscoveredCompetitor` + `CompetitorAudit` records, computes share-of-voice
7. **RECOMMENDING** — `RecommendationEngine` compares per-criterion scores against research benchmarks, generates `AuditRecommendation` records with priority/impact/code snippets
8. **COMPLETED** — Audit status updated, frontend polling stops, results displayed

**Cost tracking:** `CostTrackingService` enforces $1.00 budget cap, records per-call costs in `AuditCostLedger`

**Caching:** `AICacheService` (Redis) caches LLM responses with SHA-256 keys, 24h TTL

**Rate limiting:** `ProviderRateLimiter` (asyncio semaphore + token bucket) per AI engine

### Middleware Stack (9 layers, order matters)

From outermost to innermost:

1. `ErrorSanitizationMiddleware` — Strips stack traces in production
2. `RequestSizeLimitMiddleware` — 10MB max
3. `SecurityHeadersMiddleware` — CSP, HSTS, X-Frame-Options, Referrer-Policy
4. `RequestLoggingMiddleware` — Loguru structured logs with request IDs
5. `AuditLogMiddleware` — Security audit trail
6. `SQLInjectionProtectionMiddleware` — Pattern detection
7. `APIVersionMiddleware` — Version headers
8. `GZipMiddleware` — Compression
9. `CORSMiddleware` — Configurable origins

### Database Schema (7 migrations)

**Core tables:**

- `profiles` — Users (email, password_hash, is_active). JWT auth via `get_current_active_user` dependency
- `audits` — Audit runs (url, domain, status, crawl_data JSONB, vertical classification, brand_id FK)
- `audit_queries` — Generated queries (query_text, category, is_custom, is_editable)
- `engine_responses` — AI engine raw responses (engine, response_text, error_message, cost, latency_ms)
- `brand_mentions` — Detected brand mentions (mention_text, char_offset, confidence 0-100, context_before/after)
- `visibility_scores` — Per-audit visibility scores (overall_score, per_engine_scores JSONB, mention_count, query_mention_rate, algorithm_version="v2")
- `page_scores` — Per-page optimization scores (page_url, crawlability_score, content_structure_score, structured_data_score, authority_score, overall_page_score)
- `criterion_results` — Per-criterion results (criterion_id, category, score 0-100, passed bool, human_summary, technical_detail)
- `audit_recommendations` — Generated recommendations (criterion_id, priority high/medium/low, impact_pct, gap_score, summary, action_steps JSON, code_snippet, evidence_source, status open/done/dismissed)
- `discovered_competitors` — Competitors found in AI responses (entity_name, queries_mentioned_in UUID[], mention_count, share_of_voice, is_user_brand)
- `competitor_audits` — Competitor scoring (competitor_id FK, crawlability_avg, content_structure_avg, structured_data_avg, authority_avg)
- `audit_cost_ledger` — Cost tracking (operation_name, provider, cost Numeric(10,6), tokens_used, created_at)
- `subscriptions` — Stripe subscriptions (stripe_customer_id, stripe_subscription_id, status, tier free/pro)

**Brand voice tables** (partial implementation):

- `brand_voice_configs` — Brand voice settings
- `voice_vectors` — pgvector embeddings (1536 dims, text-embedding-3-small)
- `voice_rules` — Rules engine (forbidden_word, required_phrase, tone_directive)

**Key patterns:**

- UUIDs for all primary keys
- `created_at`/`updated_at` timestamps (auto-managed)
- JSONB columns for flexible data (crawl_data, per_engine_scores, action_steps)
- Alembic migrations in `backend/alembic/versions/` (7 migrations total)

---

## 2. Feature Completeness Matrix

| Feature | Status | Evidence | Gaps |
|---------|--------|----------|------|
| **Auth (Phase 1)** | ✅ Working | `backend/app/api/auth.py` — register/login/me endpoints. `backend/app/core/security.py` — JWT + password hashing (PyJWT, pwdlib). `backend/alembic/versions/001_add_auth_fields_to_profile.py`. All 20+ protected endpoints enforce auth via `get_current_active_user` dependency | None |
| **Audit Pipeline (Phases 2-5)** | ✅ Working | `backend/app/tasks/audit_tasks.py` — 8-stage pipeline. `backend/app/services/crawler_service.py`, `query_generator.py`, `dispatch_service.py`, `mention_detector.py`, `scoring_service.py`. `frontend/pages/audit.vue` — AuditForm, AuditProgress, AuditResults components. Polling every 2s. | None |
| **Optimization Scoring (Phase 6)** | ✅ Working | `backend/app/services/scoring/` — 4 scorer modules (CrawlabilityScorer, ContentStructureScorer, StructuredDataScorer, AuthorityScorer). 61 criteria total. `backend/app/models/page_score.py`, `criterion_result.py`. `frontend/components/OptimizationScore.vue`, `CategoryBreakdown.vue`, `CriterionDrilldown.vue`. API returns full criterion drill-down. | None |
| **Competitor Discovery (Phase 7)** | ✅ Working | `backend/app/services/competitor_service.py` — entity extraction (spaCy NER), share-of-voice calculation. `backend/app/models/competitor.py`. `frontend/components/CompetitorComparison.vue`, `CompetitorLeaderboard.vue`. | None |
| **Recommendations (Phase 8)** | ✅ Working | `backend/app/services/recommendation_engine.py` — deterministic gap analysis, 13 high-impact criteria with research benchmarks (Princeton GEO, BrightEdge, Surfer SEO, Ahrefs). Vertical-aware filtering (SaaS, eCommerce, local business, media/blog). Sentiment-based recommendations. Markdown export. `frontend/pages/recommendations.vue`, `RecommendationCard.vue`. | Needs LLM sentiment classification (service exists, not integrated) |
| **Dashboard (Phase 9)** | ✅ Working | `backend/app/services/dashboard_service.py` — aggregation across audits, PDF/CSV export (WeasyPrint, Jinja2). `frontend/pages/dashboard.vue` — DashboardHero (3 score cards), CompetitorRadar (Chart.js radar), ExportActions, TrendChart (audit history). 4 API endpoints (overview, history, export/pdf, export/csv). | None |
| **Cost Tracking** | ✅ Working | `backend/app/services/cost_service.py` — budget enforcement ($1.00 default cap). `backend/app/models/audit_cost.py` — AuditCostLedger (Numeric 10,6 precision). Alembic migration 002. Records per-call costs (LLM, embeddings). | None |
| **AI Response Cache** | ✅ Working | `backend/app/services/cache_service.py` — Redis-based, SHA-256 keys from (engine, query_text), 24h TTL. Fail-open (returns None on Redis errors). Used in `dispatch_service.py`. | None |
| **Rate Limiter** | ✅ Working | `backend/app/services/rate_limiter.py` — per-provider (asyncio semaphore + token bucket). Configured in `dispatch_service.py` ENGINE_CONFIG. Concurrent request limits + requests/sec. | None |
| **Brand Signature** | ⚠️ Partial | **Layers 1+3 working:** `backend/app/services/brand_voice.py` — rules engine (forbidden words, required phrases) + pgvector similarity (OpenAI text-embedding-3-small, 1536 dims). Hybrid score = rules×0.2 + semantic×0.5. `backend/app/api/brand_voice.py` — config, upload, rules, check endpoints. **Missing:** Layer 2 (statistical fingerprint — sentence length, vocabulary richness, readability), Layer 4 (LLM deep analysis with brand examples). | Implement `_calculate_statistical_score()` + `_llm_deep_analysis()` methods. Update scoring weights. |
| **Payments (Stripe)** | ❌ Stub | `backend/app/api/payments.py` — create-checkout, webhooks, portal, subscription-status endpoints exist. `backend/app/services/stripe_service.py` — wrapper around stripe SDK. `subscriptions` table schema exists. `frontend/composables/useStripe.ts` — client integration. **Not tested.** Env vars documented in `.env.example`. | Full integration test. Webhook verification. Error handling. Test mode validation. |
| **Jira Integration** | ❌ Stub | `backend/app/api/integrations.py` — create-task endpoint exists. `backend/app/services/jira_service.py` — Atlassian API wrapper. **Not wired.** No tests. | Wire recommendation export → Jira task creation. Test against real Jira instance. |
| **Chat Assistant (Phase 6)** | ✅ Working | `backend/app/api/chat.py` — SSE streaming endpoint. `backend/app/services/chat_service.py` — LiteLLM integration with audit context injection. `frontend/components/ChatPanel.vue` — SSE client with @microsoft/fetch-event-source. `frontend/composables/useChat.ts`. | None |
| **Code Analysis (Experimental)** | ✅ Working | `backend/app/api/code_analysis.py` — upload, analyze, results endpoints. `backend/app/services/code_analysis_service.py` — LLM-based code audit. `frontend/components/CodeAnalysisPrompts.vue`, `CodeAnalysisUpload.vue`. Pro users only. | None |
| **Legacy GEO Data Points** | ❌ Deleted | Original 108-script system (`geo_data_points/`) was deleted. Replaced by Phase 6 scoring (61 criteria). Only 5 scripts were functional (GPTBot, ClaudeBot, Schema.org, Response Time, Title Tag). Rest returned hardcoded 0. | None — intentionally removed. |
| **Celery Tasks** | ✅ Working | `backend/app/tasks/celery_app.py` — Redis broker, JSON serializer, 3 queues (geo_platform, audit, analysis). `backend/app/tasks/audit_tasks.py` — `run_crawl_and_generate` task. Task routing configured. `docker-compose.yml` — Celery worker service. | None |
| **Alembic Migrations** | ✅ Working | 7 migrations in `backend/alembic/versions/`. `backend/alembic/env.py` configured for Supabase PostgreSQL. `start.sh` runs `alembic upgrade head` before backend starts. | None |

**Summary:** 12/14 features working, 1 partial, 1 stub (payments). Core audit pipeline 100% functional.

---

## 3. Code Quality Assessment

### Backend (`backend/app/`, ~12.5k Python files in venv + project)

**Architecture:** Clean layered architecture — API routers → Services → Models. Clear separation of concerns.

**Key strengths:**

- **Pydantic validation everywhere:** All request/response schemas in `backend/app/schemas/`. Strict type checking.
- **SQLAlchemy ORM with Alembic migrations:** 7 migrations, clean migration history. No raw SQL except optimized pgvector queries.
- **Comprehensive middleware stack:** 9 custom middlewares, correctly ordered. Production-ready security headers.
- **Async-first FastAPI patterns:** `async def` for I/O-bound operations. `asyncio.run()` for sync→async bridges in Celery.
- **Loguru structured logging:** Request IDs, context injection, file rotation (500MB), 10-day retention.
- **Dependency injection:** `get_db()`, `get_current_active_user()`, `get_user_tier()` dependencies. Testable.
- **Cost tracking integration:** `CostTrackingService` tracks every LLM call. Budget enforcement before dispatch.
- **Error handling:** Try-catch blocks in services, audit status updates on failure, graceful degradation (cache fail-open).

**Key files by layer:**

| Layer | Files | Purpose |
|-------|-------|---------|
| Entry point | `backend/app/main.py` | FastAPI app, middleware registration, router includes |
| API routers | `backend/app/api/*.py` (15 files) | REST endpoints (auth, audit, analysis, brand_voice, dashboard, competitors, recommendations, payments, integrations, reports, chat, code_analysis) |
| Services | `backend/app/services/*.py` (22 files) | Business logic (analyzer, optimizer, brand_voice, crawler, query_generator, dispatch, mention_detector, scoring, competitor, recommendation_engine, dashboard, chat, code_analysis, entity_extractor, vertical_classifier, sentiment, cost, cache, rate_limiter, stripe, jira) |
| Models | `backend/app/models/*.py` (20+ files) | SQLAlchemy models (Profile, Audit, AuditQuery, EngineResponse, BrandMention, VisibilityScore, PageScore, CriterionResult, AuditRecommendation, DiscoveredCompetitor, CompetitorAudit, AuditCostLedger, Subscription, Brand, Website, BrandVoiceConfig, VoiceVector, VoiceRule, ChatSession, CodeAnalysis) |
| Schemas | `backend/app/schemas/*.py` | Pydantic request/response models |
| Core | `backend/app/core/*.py` | Config (Pydantic BaseSettings), database (SQLAlchemy engine), security (JWT auth, password hashing), middleware (9 custom middlewares), dependencies (auth, tier checking) |
| Tasks | `backend/app/tasks/*.py` | Celery app, audit task pipeline |
| Scoring | `backend/app/services/scoring/*.py` | BaseScorer, ScoringOrchestrator, 4 scorer implementations (Crawlability, ContentStructure, StructuredData, Authority) |

**Code smells found:** None critical. Only 3 TODOs:

1. `backend/app/api/integrations.py` — "TODO: Move to settings or database in production" (Stripe keys hardcoded in endpoint, should use `settings`)
2. `backend/app/api/geo_datapoints.py` — "TODO: Legacy geo_data_points/ system has been deleted" (informational comment)
3. `backend/app/core/security.py` — "TODO: Implement actual API key verification" (feature not yet built, API keys flag exists in config)

**Testing:** `pytest` configured in `requirements.txt`. No test files found in `backend/tests/` (directory missing). **Critical gap.**

### Frontend (`frontend/`, 61 Vue files)

**Architecture:** Nuxt 3 SPA mode. Auto-routing (`pages/*.vue`). Composables pattern for shared logic.

**Key strengths:**

- **Tailwind CSS design system:** Consistent color palette (primary #1E40AF, secondary #3B82F6, CTA #F59E0B). Fira Code (data/headings) + Fira Sans (body/UI) typography from `design-system/endexa-geo-platform/MASTER.md`.
- **Headless UI components:** Accessible modals, dropdowns. No custom reinventions.
- **Chart.js visualizations:** `vue-chartjs` wrapper. Radar chart (CompetitorRadar), line chart (TrendChart).
- **Composable pattern:** `frontend/composables/*.ts` (10 files) — useAuth, useApiFetch, useStripe, useReports, useChat, useBrandSelector, useCodeAnalysis, useScrollFadeIn, useSubscription, useAudit. Reusable state + API calls.
- **SSE client:** `@microsoft/fetch-event-source` for chat streaming. Proper error handling, reconnection logic.
- **Responsive design:** Mobile-first Tailwind breakpoints. Grid layouts with `grid-cols-1 md:grid-cols-2 lg:grid-cols-3`.

**Key files:**

| File | Lines | Purpose |
|------|-------|---------|
| `frontend/pages/audit.vue` | ~200 | Main audit interface — AuditForm, AuditProgress, AuditResults, export buttons, code analysis |
| `frontend/pages/dashboard.vue` | ~150 | Dashboard — DashboardHero, CompetitorRadar, TrendChart, audit selector |
| `frontend/pages/recommendations.vue` | ~180 | Recommendations list, filtering, drill-down |
| `frontend/components/AuditResults.vue` | ~250 | Visibility score, optimization score, engine breakdown, page scores |
| `frontend/components/OptimizationScore.vue` | ~150 | Category breakdown, criterion drill-down |
| `frontend/components/CategoryBreakdown.vue` | ~120 | Per-category score cards |
| `frontend/components/CriterionDrilldown.vue` | ~200 | Per-criterion detail (score, passed, technical detail) |
| `frontend/components/CompetitorRadar.vue` | ~180 | Chart.js radar + share-of-voice table |
| `frontend/components/RecommendationCard.vue` | ~160 | Priority badge, impact label, action steps, code snippet, acceptance criteria |
| `frontend/components/ChatPanel.vue` | ~200 | SSE streaming chat UI |
| `frontend/composables/useAuth.ts` | ~80 | JWT auth state, login, register, logout |
| `frontend/composables/useApiFetch.ts` | ~60 | Fetch wrapper with auth header injection |
| `frontend/nuxt.config.ts` | 55 | Nuxt config — modules (@nuxtjs/tailwindcss, @pinia/nuxt), runtime config (API URL, Stripe keys) |

**Testing:** Playwright E2E tests in `frontend/tests/e2e/` — 7 spec files (auth, brands, navigation, dashboard, audit-lifecycle, recommendations, competitors). **45 tests total** according to progression.md. Mocked API responses. No unit tests.

**Code quality issues:** None found. Clean Vue 3 Composition API. Proper use of `ref`, `computed`, `onMounted`. No mixing of Options API and Composition API.

### Configuration

**Docker Compose:** 4 services (redis, backend, celery, frontend). Health checks on redis. Volume mounts for hot reload. Depends_on constraints. **Production-ready** (just needs env-specific overrides).

**Environment variables:** `.env.example` comprehensive. 6 Stripe vars, 4 AI provider keys, database URL, Redis URL, secret key, Jira config. Frontend `.env` with API base URL and Stripe public key.

**Dependencies:**

- Backend: 78 lines in `requirements.txt`. Key deps: FastAPI 0.109.0, SQLAlchemy 2.0.25, Alembic 1.13.1, pgvector 0.2.4, LiteLLM 1.17.0, Celery 5.3.4, Redis 5.0.1, Playwright 1.41.0, Stripe 14.x, WeasyPrint 62.0, spaCy 3.7, PyJWT 2.10.1, pwdlib 0.2.1.
- Frontend: 41 lines in `package.json`. Nuxt 3.9.0, Vue 3.4.0, Tailwind 3.4.0, Chart.js 4.4.1, @microsoft/fetch-event-source 2.0.1, Playwright 1.58.2 (E2E).

---

## 4. Priority Concerns & Technical Debt

### High Priority

**H1: No backend unit tests**

- **Location:** `backend/tests/` directory missing
- **Impact:** No coverage for services, models, API endpoints. Regression risk on refactoring.
- **Fix:** Create `backend/tests/` with pytest fixtures. Cover:
  - `test_services/test_scoring_service.py` — visibility score calculation edge cases
  - `test_services/test_recommendation_engine.py` — gap analysis logic, vertical filtering
  - `test_services/test_cost_service.py` — budget enforcement
  - `test_api/test_audit.py` — audit creation, tier-aware filtering
  - `test_core/test_security.py` — JWT auth, password hashing
- **Estimate:** 2-3 days for 70% coverage on critical paths

**H2: Stripe integration untested**

- **Location:** `backend/app/api/payments.py`, `backend/app/services/stripe_service.py`
- **Impact:** Payments broken in production if webhook verification fails or subscription sync fails.
- **Fix:**
  1. Create Stripe test account, add test keys to `.env`
  2. Test create-checkout flow → verify subscription creation
  3. Test webhook handler with Stripe CLI (`stripe listen --forward-to localhost:8000/api/v1/integrations/stripe/webhook`)
  4. Test subscription status endpoint → verify tier returned
  5. Document Stripe setup in `docs/INTEGRATIONS.md`
- **Estimate:** 1 day

**H3: Brand signature incomplete (Layers 2+4 missing)**

- **Location:** `backend/app/services/brand_voice.py` — `_calculate_statistical_score()` and `_llm_deep_analysis()` methods stubbed
- **Impact:** Brand voice checking only uses rules + semantic similarity. Missing statistical fingerprint (sentence length, vocabulary richness) and LLM explanations.
- **Fix:**
  1. Implement `_calculate_statistical_score()`:
     - Average sentence length (textstat)
     - Vocabulary richness (unique words / total words)
     - Readability score (Flesch-Kincaid)
     - Formality score (passive voice detection)
     - Return 0-100 score comparing to brand baseline
  2. Implement `_llm_deep_analysis()`:
     - Load top 3 most similar brand voice vectors as examples
     - Construct LLM prompt: "Compare this text to the brand voice examples: [examples]. Explain deviations."
     - Return explanation string + 0-100 score
  3. Update hybrid scoring: rules×0.15 + stats×0.2 + semantic×0.35 + llm×0.3
- **Estimate:** 2 days

### Medium Priority

**M1: No integration tests for Celery pipeline**

- **Location:** `backend/app/tasks/audit_tasks.py`
- **Impact:** 8-stage pipeline fragile to service refactoring. No guarantee stages connect correctly.
- **Fix:** Create `backend/tests/integration/test_audit_pipeline.py`:
  - Mock external APIs (OpenAI, Anthropic, Perplexity, Gemini, Google PageSpeed)
  - Mock external services (crawler, entity extractor)
  - Test full pipeline end-to-end with fixture audit
  - Verify audit status transitions, data persisted at each stage
- **Estimate:** 1 day

**M2: No error monitoring (Sentry DSN empty)**

- **Location:** `backend/app/core/config.py` — SENTRY_DSN=""
- **Impact:** Production errors invisible. No alerting.
- **Fix:**
  1. Create Sentry project (sentry.io)
  2. Add DSN to `.env`
  3. Configure `sentry_sdk.init()` in `backend/app/main.py`
  4. Test error capture with intentional exception
- **Estimate:** 1 hour

**M3: Rate limiter not exposed to frontend**

- **Location:** Middleware adds `X-RateLimit-*` headers but frontend doesn't read them
- **Impact:** Users hit rate limit without warning.
- **Fix:**
  1. Add rate limit state to `useApiFetch.ts` composable
  2. Parse `X-RateLimit-Remaining` from response headers
  3. Show warning toast when remaining < 5
  4. Show upgrade prompt when limit hit (429 response)
- **Estimate:** 4 hours

**M4: No database connection pooling config**

- **Location:** `backend/app/core/database.py` — uses defaults (pool_size=5, max_overflow=10)
- **Impact:** Connection exhaustion under load (100+ concurrent requests).
- **Fix:**
  1. Increase pool_size to 20 in production (config.py: DB_POOL_SIZE=20, DB_MAX_OVERFLOW=40)
  2. Add connection pool metrics to `/health` endpoint
  3. Document in `docs/DEPLOYMENTS.md`
- **Estimate:** 2 hours

### Low Priority

**L1: No API documentation versioning**

- **Location:** OpenAPI docs at `/api/v1/docs` don't mention version deprecation policy
- **Impact:** Breaking changes confuse API consumers.
- **Fix:** Add `docs/API-VERSIONING.md` with:
  - Current version: v1
  - Deprecation policy: 6 months notice, parallel versions supported
  - Migration guides for breaking changes
- **Estimate:** 1 hour

**L2: Frontend E2E tests use mocked API**

- **Location:** `frontend/tests/e2e/*.spec.ts` — all API responses are mocked
- **Impact:** Tests don't catch backend API contract changes.
- **Fix:**
  1. Add `TEST_MODE` env var to backend
  2. Add seed data script (`backend/scripts/seed_test_data.py`)
  3. Run E2E tests against real backend in CI
  4. Keep mocked tests for offline development
- **Estimate:** 1 day

**L3: No database backups documented**

- **Location:** `docs/DEPLOYMENTS.md` doesn't mention backup strategy
- **Impact:** Data loss risk.
- **Fix:** Document Supabase backup strategy:
  - Supabase free tier: daily backups, 7-day retention
  - Pro tier: point-in-time recovery (7 days)
  - Export strategy: `pg_dump` weekly to S3 (document script)
- **Estimate:** 2 hours

**L4: Missing API rate limiting per user**

- **Location:** Middleware rate limiting is global, not per-user
- **Impact:** One user can exhaust rate limit for all users.
- **Fix:**
  1. Implement per-user rate limiter using Redis (key: `rate_limit:{user_id}`)
  2. Use sliding window algorithm
  3. Apply to POST endpoints only (GET are read-only)
- **Estimate:** 4 hours

---

## 5. Testing Coverage

### Current State

**Backend:**

- Unit tests: **0** (no `backend/tests/` directory)
- Integration tests: **0**
- E2E tests: **0**

**Frontend:**

- Unit tests: **0**
- Component tests: **0**
- E2E tests: **45** (Playwright, mocked API)

**Coverage estimate:** ~5% (E2E tests only, mocked responses)

### Recommended Testing Strategy

**Backend priority:**

1. **Services layer** (highest ROI):
   - `test_scoring_service.py` — visibility score edge cases (0 mentions, 100% mention rate, mixed confidence)
   - `test_recommendation_engine.py` — gap analysis, vertical filtering, sentiment recommendations, markdown export
   - `test_cost_service.py` — budget enforcement, cost tracking, budget exceeded scenarios
   - `test_crawler_service.py` — HTML parsing, schema extraction, error handling
   - `test_query_generator.py` — brand name extraction, LLM query generation (mocked LLM)
2. **API layer** (integration):
   - `test_audit.py` — POST /audit (201), GET /audit/{id} (tier filtering), custom query CRUD
   - `test_auth.py` — register, login, token refresh, protected endpoints
   - `test_recommendations.py` — GET, PATCH status, export markdown
3. **Celery tasks** (integration):
   - `test_audit_pipeline.py` — mock external APIs, test 8-stage pipeline end-to-end

**Frontend priority:**

1. Keep E2E tests (already good coverage)
2. Add component tests for complex components:
   - `CriterionDrilldown.test.ts` — props validation, score display
   - `CompetitorRadar.test.ts` — chart rendering, data transformation
   - `RecommendationCard.test.ts` — priority badge, action steps, code snippet rendering

**Target:** 70% coverage on backend services, 80% coverage on API endpoints, 100% E2E coverage on critical user flows.

---

## 6. Architecture Strengths

1. **Clean separation of concerns:** API routers → Services → Models. No business logic in API layer.
2. **Async-first design:** FastAPI async endpoints, asyncio for concurrent AI calls, Celery for long-running tasks.
3. **Production-ready middleware stack:** Security headers, request logging, audit logging, SQL injection protection, error sanitization.
4. **Comprehensive data model:** 20+ SQLAlchemy models with proper relationships, migrations, JSONB for flexibility.
5. **Cost-aware AI integration:** Budget enforcement, per-call cost tracking, cache to reduce costs.
6. **Dual-score system:** Visibility (AI mention-based) + Optimization (criteria-based). Complementary metrics.
7. **Research-backed recommendations:** 13 high-impact criteria with evidence from Princeton, BrightEdge, Surfer SEO, Ahrefs.
8. **Vertical-aware logic:** Classifier detects SaaS/eCommerce/local/media, filters irrelevant recommendations (e.g., no Product schema for SaaS).
9. **Modular frontend components:** 28 Vue components, 10 composables, clear component hierarchy.
10. **Docker Compose for local dev:** One-command setup (`./start.sh`), health checks, volume mounts for hot reload.

---

## 7. Architecture Weaknesses

1. **No backend tests:** Critical gap. Services layer has complex logic (scoring, recommendations) with no test coverage.
2. **Stripe untested:** Payments feature exists but never tested. High risk for production.
3. **Brand signature incomplete:** 2 of 4 layers working. Missing statistical fingerprint and LLM deep analysis.
4. **No error monitoring:** Sentry DSN empty, no production error visibility.
5. **Rate limiting not user-aware:** Global rate limit, not per-user. One user can exhaust limit.
6. **E2E tests use mocked API:** Frontend tests don't catch backend contract changes.
7. **No database backup strategy documented:** Data loss risk.
8. **No CI/CD pipeline:** No automated testing, linting, deployment. Manual process.

---

## 8. Recommendations for Next Steps

### Immediate (Week 1)

1. **Add backend unit tests** (H1) — Focus on `scoring_service.py`, `recommendation_engine.py`, `cost_service.py`. Target 70% coverage.
2. **Test Stripe integration** (H2) — Use Stripe test mode, verify webhook handler, document setup.
3. **Configure Sentry** (M2) — 1 hour task, immediate production value.

### Short-term (Weeks 2-4)

4. **Complete brand signature** (H3) — Implement layers 2+4. Update scoring weights.
5. **Add Celery pipeline integration tests** (M1) — Mock external APIs, test 8-stage pipeline end-to-end.
6. **Improve rate limiter** (M3, L4) — Per-user rate limiting with Redis, expose limits to frontend.
7. **Document deployment** (L3) — Backup strategy, database connection pooling, API versioning policy.

### Long-term (Month 2+)

8. **CI/CD pipeline** — GitHub Actions: pytest on every PR, Playwright E2E on main, auto-deploy to staging.
9. **Real E2E tests** (L2) — Run Playwright against real backend in CI, keep mocked tests for offline dev.
10. **Monitoring dashboard** — Grafana + Prometheus for API latency, Celery queue depth, LLM cost per day.
11. **Performance optimization:** Database query optimization (N+1 queries on audit detail endpoint), Redis cache warming, CDN for static assets.

---

## 9. Key File Locations

### Backend Critical Paths

| Purpose | File |
|---------|------|
| App entry point | `backend/app/main.py` |
| Audit pipeline (Celery) | `backend/app/tasks/audit_tasks.py` |
| Crawling | `backend/app/services/crawler_service.py` |
| Query generation | `backend/app/services/query_generator.py` |
| AI dispatch | `backend/app/services/dispatch_service.py` |
| Mention detection | `backend/app/services/mention_detector.py` |
| Visibility scoring | `backend/app/services/scoring_service.py` |
| Optimization scoring | `backend/app/services/scoring/scoring_orchestrator.py` |
| Competitor discovery | `backend/app/services/competitor_service.py` |
| Recommendations | `backend/app/services/recommendation_engine.py` |
| Dashboard export | `backend/app/services/dashboard_service.py` |
| Cost tracking | `backend/app/services/cost_service.py` |
| AI cache | `backend/app/services/cache_service.py` |
| Rate limiter | `backend/app/services/rate_limiter.py` |
| Auth | `backend/app/core/security.py` |
| Config | `backend/app/core/config.py` |
| Database | `backend/app/core/database.py` |
| Middleware | `backend/app/core/middleware.py` |
| Audit API | `backend/app/api/audit.py` |
| Auth API | `backend/app/api/auth.py` |
| Recommendations API | `backend/app/api/recommendations.py` |
| Payments API | `backend/app/api/payments.py` |
| Audit model | `backend/app/models/audit.py` |
| Visibility score model | `backend/app/models/visibility_score.py` |
| Page score model | `backend/app/models/page_score.py` |
| Recommendation model | `backend/app/models/audit_recommendation.py` |
| Migrations | `backend/alembic/versions/*.py` |

### Frontend Critical Paths

| Purpose | File |
|---------|------|
| Audit page | `frontend/pages/audit.vue` |
| Dashboard page | `frontend/pages/dashboard.vue` |
| Recommendations page | `frontend/pages/recommendations.vue` |
| Audit results | `frontend/components/AuditResults.vue` |
| Optimization score | `frontend/components/OptimizationScore.vue` |
| Category breakdown | `frontend/components/CategoryBreakdown.vue` |
| Criterion drill-down | `frontend/components/CriterionDrilldown.vue` |
| Competitor radar | `frontend/components/CompetitorRadar.vue` |
| Recommendation card | `frontend/components/RecommendationCard.vue` |
| Chat panel | `frontend/components/ChatPanel.vue` |
| Auth composable | `frontend/composables/useAuth.ts` |
| API fetch composable | `frontend/composables/useApiFetch.ts` |
| Audit composable | `frontend/composables/useAudit.ts` |
| Nuxt config | `frontend/nuxt.config.ts` |
| Tailwind config | `frontend/tailwind.config.ts` |

### Configuration & Documentation

| Purpose | File |
|---------|------|
| Docker Compose | `docker-compose.yml` |
| Backend env template | `backend/.env.example` |
| Frontend env template | `frontend/.env.example` |
| Backend dependencies | `backend/requirements.txt` |
| Frontend dependencies | `frontend/package.json` |
| Project guide | `CLAUDE.md` |
| Progression tracker | `docs/progression.md` |
| API reference | `docs/API-REFERENCE.md` |
| Architecture docs | `docs/ARCHITECTURE.md` |
| Backlog | `docs/BACKLOG.md` |
| Connections | `docs/CONNECTIONS.md` |
| Incidents | `docs/INCIDENTS.md` |
| Security | `docs/SECURITY.md` |
| Testing strategy | `docs/TESTING-STRATEGY.md` |

---

## 10. Dependency Health

### Backend (Python 3.11+)

**Critical dependencies:**

- ✅ FastAPI 0.109.0 — Stable, well-maintained
- ✅ SQLAlchemy 2.0.25 — Latest stable, good migration path from 1.x
- ✅ Alembic 1.13.1 — Stable, actively maintained
- ✅ pgvector 0.2.4 — PostgreSQL extension, stable
- ⚠️ LiteLLM 1.17.0 — Fast-moving, breaking changes in minor versions (update strategy needed)
- ✅ Celery 5.3.4 — Stable, production-ready
- ✅ Redis 5.0.1 — Stable
- ✅ Playwright 1.41.0 — Stable, good for web scraping
- ✅ Stripe 14.x — Major version, stable API
- ✅ PyJWT 2.10.1 — Stable
- ✅ pwdlib 0.2.1 — Modern password hashing, good Argon2 support

**Outdated/risky:**

- ⚠️ LiteLLM 1.17.0 — Current version is 1.40+. Breaking changes in 1.20, 1.30. **Pin to 1.17.x** or budget upgrade time.
- ✅ All other deps current within minor versions.

### Frontend (Node 18+)

**Critical dependencies:**

- ✅ Nuxt 3.9.0 — Stable, current is 3.11
- ✅ Vue 3.4.0 — Stable, current is 3.4.x
- ✅ Tailwind 3.4.0 — Latest stable
- ✅ Chart.js 4.4.1 — Stable
- ✅ Playwright 1.58.2 — Latest (testing)
- ✅ @microsoft/fetch-event-source 2.0.1 — Stable, no updates needed

**Outdated/risky:** None. All deps within 1-2 minor versions of latest.

### Recommendation

**LiteLLM pinning strategy:**

1. Pin to `litellm==1.17.0` in `requirements.txt` (already done)
2. Monitor breaking changes in [LiteLLM changelog](https://github.com/BerriAI/litellm/releases)
3. Budget 2-day upgrade sprint every 6 months
4. Test with backup OpenAI SDK fallback

---

## Summary Statistics

**Codebase size:**

- Backend: 12,511 Python files (including venv), ~100 project files
- Frontend: 61 Vue files, 10 composables
- Total lines of code: ~15,000 (estimated, excluding venv)

**Database:**

- 22 tables
- 7 migrations
- pgvector for embeddings (1536 dims)

**API endpoints:**

- 50+ REST endpoints across 15 routers
- Auth: 3 endpoints (register, login, me)
- Audit: 8 endpoints (create, list, get, custom query CRUD)
- Recommendations: 4 endpoints (list, update status, export markdown)
- Dashboard: 4 endpoints (overview, history, PDF/CSV export)
- Payments: 4 endpoints (create-checkout, webhooks, portal, subscription-status)
- Integrations: 2 endpoints (Stripe webhook, Jira task creation)
- Chat: 1 endpoint (SSE streaming)
- Code analysis: 3 endpoints (upload, analyze, results)

**Test coverage:**

- Backend: 0% (no tests)
- Frontend: ~40% E2E coverage (45 Playwright tests, mocked API)

**Documentation:**

- 15+ markdown docs in `docs/`
- OpenAPI auto-generated at `/api/v1/docs`
- Design system in `design-system/endexa-geo-platform/MASTER.md`

---

**End of Repository Map**

*Last updated: 2026-03-26*
