# API Reference

> All endpoints under `/api/v1/`. Full interactive docs at `http://localhost:8000/api/v1/docs` (dev mode only).

**Authentication:** All audit-related endpoints require a JWT Bearer token. Obtain one via `/api/v1/auth/register` or `/api/v1/auth/login`. Pass as `Authorization: Bearer <token>`.

---

## Authentication (`/api/v1/auth/`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/register` | Create account | No |
| POST | `/login` | Authenticate and get JWT | No |
| GET | `/me` | Get current user info | Yes |

### POST /register

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "SecurePass123!", "full_name": "John Doe"}'
```

**Password policy:** Min 12 chars, requires uppercase + lowercase + digit + special character.

**Response:**
```json
{"access_token": "eyJ...", "refresh_token": null, "token_type": "bearer"}
```

### POST /login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "SecurePass123!"}'
```

**Response:**
```json
{"access_token": "eyJ...", "refresh_token": "eyJ...", "token_type": "bearer"}
```

### GET /me

```bash
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <access_token>"
```

**Response:**
```json
{"id": "uuid", "email": "user@example.com", "full_name": "John Doe", "role": "user"}
```

---

## Analysis (`/api/v1/analysis/`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/analyze` | Start URL analysis | Yes |
| GET | `/{analysis_id}` | Get analysis results | Yes |
| GET | `/history` | Get analysis history | Yes |

### POST /analyze

```bash
curl -X POST http://localhost:8000/api/v1/analysis/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "keywords": ["web", "design"]}'
```

**Response:**
```json
{"analysis_id": "uuid", "status": "pending"}
```

### GET /{analysis_id}

```json
{
  "id": "uuid",
  "url": "https://example.com",
  "status": "completed",
  "geo_score": 75,
  "visibility_score": 80,
  "readability_score": 70,
  "authority_score": 75,
  "created_at": "2026-02-21T10:00:00Z"
}
```

---

## GEO Data Points (`/api/v1/geo-datapoints/`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/run` | Run 108-point measurement | Yes |
| GET | `/{analysis_id}` | Get full results | Yes |
| GET | `/{analysis_id}/summary` | Get summary scores | Yes |
| GET | `/{analysis_id}/module/{module}` | Get module detail | Yes |

### POST /run

```bash
curl -X POST http://localhost:8000/api/v1/geo-datapoints/run \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "modules": ["wi", "cnt"]}'
```

---

## Optimization (`/api/v1/optimization/`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/generate` | Generate recommendations | Yes |
| GET | `/recommendations/{analysis_id}` | Get recommendations | Yes |

> **Note:** Currently a stub. Returns empty/mock data until LLM integration is complete (BACKLOG Priority 1).

---

## Brand Signature (`/api/v1/voice/`)

4-layer brand signature engine. See `docs/ARCHITECTURE.md` for full design.

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/config` | Create brand signature config | Yes |
| GET | `/config/{id}` | Get config details + stats | Yes |
| POST | `/config/{id}/upload` | Upload knowledge base (TXT) | Yes |
| POST | `/config/{id}/rule` | Add rule (forbidden_word, required_phrase, tone_directive) | Yes |
| POST | `/check` | Check content — fast mode (layers 1-3) | Yes |
| POST | `/explain` | Deep analysis — all 4 layers (planned) | Yes |

### POST /check (Fast Mode — Layers 1-3)

```bash
curl -X POST http://localhost:8000/api/v1/voice/check \
  -H "Content-Type: application/json" \
  -d '{"text": "Your content here", "config_id": "uuid"}'
```

**Response:**
```json
{
  "overall_score": 85,
  "vector_score": 90,
  "rule_score": 75,
  "stats_score": null,
  "violations": [],
  "suggestions": []
}
```

**Current scoring:** `overall = (vector_score * 0.7) + (rule_score * 0.3)`
**Target scoring:** `overall = (rules * 0.2) + (stats * 0.3) + (semantic * 0.5)` — when Layer 2 is built.

---

## Dashboard (`/api/v1/dashboard/`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/stats` | Dashboard metrics | Yes |
| GET | `/recent` | Recent analyses | Yes |

---

## Integrations (`/api/v1/integrations/`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/stripe/webhook` | Stripe payment webhook | Stripe signature |
| POST | `/stripe/checkout` | Create Stripe checkout session | Yes |
| POST | `/jira/create-issue` | Create Jira ticket | Yes |

> **Note:** Both are stubs until payment and recommendation features are complete.

---

## Health & Info

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | API info + version |
| GET | `/health` | Health check |
| GET | `/security-info` | Security config (dev only) |

---

## Rate Limits

| Tier | Limit |
|------|-------|
| Free | 3 analyses/day |
| Pro | 100 analyses/day |
| Enterprise | 1000 analyses/day |

Rate limit headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Human-readable error message",
  "request_id": "uuid"  // production only
}
```

| Status | Meaning |
|--------|---------|
| 400 | Bad request (validation error) |
| 401 | Unauthorized (missing or invalid JWT) |
| 404 | Resource not found |
| 429 | Rate limit exceeded |
| 500 | Internal server error |
