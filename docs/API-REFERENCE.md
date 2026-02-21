# API Reference

> All endpoints under `/api/v1/`. Full interactive docs at `http://localhost:8000/api/v1/docs` (dev mode only).

---

## Analysis (`/api/v1/analysis/`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/analyze` | Start URL analysis | No (MVP) |
| GET | `/{analysis_id}` | Get analysis results | No (MVP) |
| GET | `/history` | Get analysis history | No (MVP) |

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
| POST | `/run` | Run 108-point measurement | No (MVP) |
| GET | `/{analysis_id}` | Get full results | No (MVP) |
| GET | `/{analysis_id}/summary` | Get summary scores | No (MVP) |
| GET | `/{analysis_id}/module/{module}` | Get module detail | No (MVP) |

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
| POST | `/generate` | Generate recommendations | No (MVP) |
| GET | `/recommendations/{analysis_id}` | Get recommendations | No (MVP) |

> **Note:** Currently a stub. Returns empty/mock data until LLM integration is complete (BACKLOG Priority 1).

---

## Brand Signature (`/api/v1/voice/`)

4-layer brand signature engine. See `docs/ARCHITECTURE.md` for full design.

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/config` | Create brand signature config | No (MVP) |
| GET | `/config/{id}` | Get config details + stats | No (MVP) |
| POST | `/config/{id}/upload` | Upload knowledge base (TXT) | No (MVP) |
| POST | `/config/{id}/rule` | Add rule (forbidden_word, required_phrase, tone_directive) | No (MVP) |
| POST | `/check` | Check content — fast mode (layers 1-3) | No (MVP) |
| POST | `/explain` | Deep analysis — all 4 layers (planned) | No (MVP) |

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
| GET | `/stats` | Dashboard metrics | No (MVP) |
| GET | `/recent` | Recent analyses | No (MVP) |

---

## Integrations (`/api/v1/integrations/`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/stripe/webhook` | Stripe payment webhook | Stripe signature |
| POST | `/jira/create-issue` | Create Jira ticket | No (MVP) |

> **Note:** Both are stubs until payment and recommendation features are complete.

---

## Health & Info

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | API info + version |
| GET | `/health` | Health check |
| GET | `/security-info` | Security config (dev only) |

---

## Rate Limits (when auth is enabled)

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
| 401 | Unauthorized (when auth enabled) |
| 404 | Resource not found |
| 429 | Rate limit exceeded |
| 500 | Internal server error |
