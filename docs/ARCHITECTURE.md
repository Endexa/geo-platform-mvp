# System Architecture

> How the system is built, how data flows, and why decisions were made.

---

## Service Boundaries

```
┌─────────────────────────────────────────────────┐
│                   Browser                        │
│              Nuxt 3 SPA (:3000)                  │
└───────────────────┬─────────────────────────────┘
                    │ HTTP/REST
┌───────────────────▼─────────────────────────────┐
│              FastAPI Backend (:8000)              │
│  ┌──────┐ ┌───────────┐ ┌──────────┐ ┌───────┐ │
│  │ API  │ │ Services  │ │ Middleware│ │ Auth  │ │
│  │Routes│ │(analyzer, │ │(security,│ │(JWT,  │ │
│  │      │ │ optimizer,│ │ logging, │ │ RLS)  │ │
│  │      │ │ brand_v.) │ │ audit)   │ │       │ │
│  └──┬───┘ └─────┬─────┘ └──────────┘ └───────┘ │
│     │           │                                │
│  ┌──▼───────────▼────┐  ┌───────────────────┐   │
│  │   SQLAlchemy ORM  │  │   Celery Worker   │   │
│  └────────┬──────────┘  └────────┬──────────┘   │
└───────────┼──────────────────────┼───────────────┘
            │                      │
  ┌─────────▼──────┐    ┌─────────▼──────┐
  │ PostgreSQL 15  │    │   Redis 7      │
  │  + pgvector    │    │ (cache+broker) │
  └────────────────┘    └────────────────┘
```

---

## Data Flow: URL Analysis

```
1. User enters URL + keywords on /analyze page
2. Frontend POST /api/v1/analysis/analyze {url, keywords}
3. Backend creates Analysis record (status=pending), returns analysis_id
4. Celery task queued → AnalyzerService.run(url, keywords)
5. AnalyzerService:
   a. Fetches URL (requests/BeautifulSoup)
   b. Extracts text, headings, meta tags
   c. Calculates Visibility (keywords in H1/H2)
   d. Calculates Readability (Flesch-Kincaid via textstat)
   e. Calculates Authority (domain heuristic)
   f. Computes GEO Score = weighted average
   g. Updates Analysis record (status=completed, scores)
6. Frontend polls GET /api/v1/analysis/{id} every 2s
7. When status=completed, displays score cards
```

---

## Data Flow: GEO Data Points (108 measurements)

```
1. POST /api/v1/geo-datapoints/run {url, modules?}
2. Orchestrator (run_all.py) invoked
3. For each enabled module (WI, CNT, BV, SEO, UX, COMP, LEG):
   a. Load measurement scripts for module
   b. Run each script async (with timeout)
   c. Each script returns: {score: 0-100, comment, metadata}
4. Aggregate module scores (average of data points)
5. Compute overall GEO score (weighted module average)
6. Store results in DB
7. Return summary + per-module breakdown
```

---

## Database Schema

### Core Tables

| Table | Purpose |
|-------|---------|
| `analyses` | URL analysis records (url, status, scores, timestamps) |
| `websites` | Registered website records |
| `recommendations` | AI-generated optimization recommendations |
| `brand_voice_configs` | Brand voice configuration + rules |
| `brand_voice_knowledge` | Stored vectors for brand voice similarity |
| `organizations` | Multi-tenant org records |
| `profiles` | User profiles (email, password_hash, is_active for auth) |
| `audit_cost_ledger` | Per-API-call cost tracking (engine, model, tokens, cost_usd) |

### Key Relationships

```
organizations 1──N profiles
organizations 1──N websites
websites      1──N analyses
analyses      1──N recommendations
analyses      1──N audit_cost_ledger
organizations 1──N brand_voice_configs
brand_voice_configs 1──N brand_voice_knowledge
```

### Vector Storage

Brand voice uses PostgreSQL pgvector for embedding storage:
```sql
-- brand_voice_knowledge table
embedding VECTOR(1536)  -- OpenAI text-embedding-3-small dimensions
```

---

## Middleware Stack

Applied in order (outermost → innermost):

| # | Middleware | Purpose |
|---|-----------|---------|
| 1 | ErrorSanitizationMiddleware | Strips stack traces in production |
| 2 | RequestSizeLimitMiddleware | Rejects requests > 10MB |
| 3 | SecurityHeadersMiddleware | CSP, HSTS, X-Frame-Options, X-Content-Type-Options |
| 4 | RequestLoggingMiddleware | Logs all requests with timing |
| 5 | AuditLogMiddleware | Audit trail for sensitive operations |
| 6 | SQLInjectionProtectionMiddleware | Scans request params for SQL patterns |
| 7 | APIVersionMiddleware | Adds API version headers |
| 8 | GZipMiddleware | Compresses responses > 1KB |
| 9 | TrustedHostMiddleware | Production only — validates Host header |
| 10 | CORSMiddleware | Cross-origin access control |

---

## Rate Limiting

### Inbound (per-user)

| Tier | Limit | Intended For |
|------|-------|-------------|
| Free | 3 analyses/day | Trial users |
| Pro | 100 analyses/day | Paying customers |
| Enterprise | 1000 analyses/day | Large agencies |

Implemented in `backend/app/core/rate_limiter.py`. Auth is now enabled on all protected endpoints.

### Outbound (per-AI-provider)

Prevents exceeding AI engine API rate limits. Implemented in `backend/app/core/outbound_limiter.py`.

| Provider | RPM | Max Concurrent |
|----------|-----|----------------|
| OpenAI | 60 | 10 |
| Anthropic | 60 | 10 |
| Perplexity | 20 | 5 |

Uses asyncio.Semaphore for concurrency control + token bucket for RPM pacing. Callers block (back-pressure) until capacity is available.

---

## Cost Tracking

Implemented in `backend/app/services/cost_service.py` with `backend/app/models/audit_cost.py`.

- Every outbound AI API call records: engine, model, prompt_tokens, completion_tokens, cost_usd (Numeric 10,6), cached flag
- Per-audit budget enforcement: `CostTrackingService.check_budget()` returns False when spend exceeds cap
- Default budget: $1.00 per audit (configurable via `settings.AUDIT_BUDGET_USD`)

---

## AI Response Caching

Implemented in `backend/app/services/cache_service.py`.

- Redis-based async cache for AI API responses
- Deterministic SHA-256 cache keys from (engine, model, messages, temperature)
- TTL: 24 hours (configurable via `settings.AI_CACHE_TTL_SECONDS`)
- Fail-open design: Redis outage logs a warning but does not block AI calls

---

## Brand Signature Engine (4-Layer Architecture)

### Overview

The Brand Signature module answers: "Does this new content sound like it came from this brand?" It uses 4 independent layers, each catching different types of brand drift that others miss.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   BRAND SIGNATURE CHECK                      │
│                                                              │
│  Input: new content to check + brand config_id               │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐     │
│  │  Layer 1: RULES ENGINE         (instant, $0)        │     │
│  │  ├─ Forbidden words            → -20pts each        │     │
│  │  ├─ Required phrases           → -10pts if missing  │     │
│  │  └─ Tone directives            → suggestions        │     │
│  │  Status: WORKING (brand_voice.py _check_rules)      │     │
│  └─────────────────────────────────────────────────────┘     │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐     │
│  │  Layer 2: STATISTICAL FINGERPRINT (< 100ms, $0)     │     │
│  │  ├─ Avg sentence length        vs brand norm        │     │
│  │  ├─ Vocabulary richness (TTR)  vs brand norm        │     │
│  │  ├─ Readability (Flesch)       vs brand range       │     │
│  │  ├─ Passive voice ratio        vs brand norm        │     │
│  │  ├─ Question frequency         vs brand norm        │     │
│  │  └─ Formality score            vs brand norm        │     │
│  │  Status: NOT YET BUILT                              │     │
│  └─────────────────────────────────────────────────────┘     │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐     │
│  │  Layer 3: SEMANTIC SIMILARITY  (< 500ms, ~$0.001)   │     │
│  │  ├─ Embed new content (OpenAI)                      │     │
│  │  ├─ Retrieve top-5 brand chunks (pgvector <=>)      │     │
│  │  ├─ Avg cosine similarity → 0-100 score             │     │
│  │  └─ Distance from brand centroid (planned)          │     │
│  │  Status: WORKING (brand_voice.py _calculate_vector) │     │
│  └─────────────────────────────────────────────────────┘     │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐     │
│  │  Layer 4: LLM DEEP ANALYSIS   (2-5s, ~$0.02)       │     │
│  │  ├─ Triggered on-demand ("Explain" button)          │     │
│  │  ├─ Retrieves similar brand passages from pgvector  │     │
│  │  ├─ LLM compares tone, style, messaging             │     │
│  │  └─ Returns suggestions with brand excerpt examples │     │
│  │  Status: NOT YET BUILT                              │     │
│  └─────────────────────────────────────────────────────┘     │
│                                                              │
│  Composite Score:                                            │
│  Fast (L1-3): rules×0.2 + stats×0.3 + semantic×0.5          │
│  Deep (L1-4): rules×0.15 + stats×0.2 + semantic×0.35        │
│               + llm×0.3                                      │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow: Brand Signature Check

```
1. User uploads brand content (PDF/TXT) to knowledge base
   a. Text chunked into ~500-char paragraphs
   b. Each chunk embedded via OpenAI text-embedding-3-small
   c. Chunks + embeddings stored in voice_vectors (pgvector)
   d. Brand stats profile extracted and stored (Layer 2, planned)

2. User submits new content to check
   a. Layer 1: Scan for forbidden words, check required phrases → instant score
   b. Layer 2: Compute text stats, compare against brand profile → fast score
   c. Layer 3: Embed content, query pgvector for top-5 similar chunks → similarity score
   d. Composite score returned (layers 1-3)

3. User clicks "Explain" (optional)
   a. Layer 4: Retrieve brand passages + send to LLM with comparison prompt
   b. LLM returns: tone mismatches, vocabulary drift, missing messages
   c. Detailed report with brand excerpts as evidence
```

### What Each Layer Catches

| Signal | L1 Rules | L2 Stats | L3 Vectors | L4 LLM |
|--------|----------|----------|------------|--------|
| Forbidden word "cheap" | Yes | | | |
| Sentences too long for brand | | Yes | | |
| Content sounds like competitor | | | Yes | |
| Tone shifted formal→casual | | Partial | | Yes |
| Missing key brand message | Yes | | | Yes |
| Vocabulary too technical | | Yes | | Yes |
| "Why doesn't this match?" | | | | Yes |

### Database Schema (Brand Signature)

```
brand_voice_configs
├── id UUID PK
├── org_id UUID FK → organizations
├── name TEXT
├── description TEXT
└── stats_profile JSONB (planned — Layer 2 brand norms)

voice_vectors
├── id UUID PK
├── config_id UUID FK → brand_voice_configs
├── content_chunk TEXT
└── embedding VECTOR(1536) — pgvector, OpenAI text-embedding-3-small

voice_rules
├── id UUID PK
├── config_id UUID FK → brand_voice_configs
├── rule_type TEXT ('forbidden_word' | 'required_phrase' | 'tone_directive')
└── value TEXT
```

### Why This Architecture (Not Pure RAG)

1. **Layers 1-3 are instant and free** — suitable for real-time "check as you type". Pure RAG always needs an LLM call.
2. **Layer 2 (stats) is the secret weapon** — catches style drift that neither rules nor vectors detect. Brand uses 15-word sentences? A 40-word academic paragraph will have high vector similarity (same topic) but Layer 2 flags it instantly.
3. **Layer 4 is on-demand** — expensive LLM analysis only when user wants it. Not per-keystroke.
4. **No external infrastructure** — PostgreSQL + pgvector handles everything. No MongoDB, no Qdrant.

---

## Authentication

Implemented in `backend/app/core/security.py`, `backend/app/api/auth.py`, `backend/app/services/auth_service.py`.

- **Library:** PyJWT (JWT creation/verification) + pwdlib (bcrypt password hashing)
- **Endpoints:** POST /register, POST /login, GET /me
- **Enforcement:** All audit-related endpoints require `Depends(get_current_active_user)`
- **Public endpoints:** /health, /, /security-info, /api/v1/auth/register, /api/v1/auth/login
- **Password policy:** Min 12 chars, requires uppercase + lowercase + digit + special character
- **Token expiry:** Access tokens 30 min, Refresh tokens 7 days

---

## Security Details

Full security documentation: `docs/SECURITY.md`

Key features:
- JWT authentication with PyJWT (enabled on all protected endpoints)
- Password hashing with pwdlib (bcrypt)
- Password policy: 12+ chars, uppercase, lowercase, digits, special
- SQL injection protection via ORM + middleware
- XSS protection via Pydantic validation
- CSRF protection middleware
- Request size limits
- Security headers (CSP, HSTS)
- Audit logging
