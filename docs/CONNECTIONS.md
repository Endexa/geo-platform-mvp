# External Connections & Health Checks

> Run these checks when things break. Each connection includes a curl command to verify it's alive.

---

## Architecture

```
Browser (Nuxt 3)
  └─> FastAPI Backend (:8000)
        ├─> PostgreSQL + pgvector (:5432)
        ├─> Redis (:6379) — cache + Celery broker
        ├─> OpenAI API — LLM for recommendations (not yet integrated)
        ├─> Stripe API — payments (stub)
        └─> Jira API — ticket creation (stub)
```

---

## 1. Backend API

```bash
# Health check
curl http://localhost:8000/health
# Expected: {"status":"healthy","environment":"development","version":"1.0.0"}

# API docs (dev only)
curl -s http://localhost:8000/api/v1/docs | head -20
# Expected: HTML Swagger UI
```

## 2. PostgreSQL (pgvector)

```bash
# Via Docker
docker-compose exec postgres pg_isready -U postgres
# Expected: accepting connections

# Check pgvector extension
docker-compose exec postgres psql -U postgres -d geo_platform -c "SELECT extname FROM pg_extension WHERE extname = 'vector';"
# Expected: vector

# Check tables exist
docker-compose exec postgres psql -U postgres -d geo_platform -c "\dt"
```

## 3. Redis

```bash
# Via Docker
docker-compose exec redis redis-cli ping
# Expected: PONG

# Check Celery broker
docker-compose exec redis redis-cli info clients
```

## 4. Celery Worker

```bash
# Check worker is running
docker-compose logs celery | tail -5
# Expected: "celery@... ready"

# Check active tasks
docker-compose exec celery celery -A app.tasks.celery_app inspect active
```

## 5. OpenAI API (when integrated)

```bash
# Verify API key works
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY" | jq '.data[0].id'
# Expected: model ID string
```

## 6. Stripe (when integrated)

```bash
# Verify API key
curl https://api.stripe.com/v1/balance \
  -u "$STRIPE_SECRET_KEY:" | jq '.available'
# Expected: balance array
```

## 7. Jira (when integrated)

```bash
# Verify connection
curl -s "$JIRA_BASE_URL/rest/api/2/myself" \
  -H "Authorization: Bearer $JIRA_API_TOKEN" | jq '.displayName'
# Expected: your Jira display name
```

---

## Quick Status Dashboard

```bash
echo "=== GEO Platform Health ==="
echo -n "Backend:    " && curl -s http://localhost:8000/health | jq -r '.status' 2>/dev/null || echo "DOWN"
echo -n "PostgreSQL: " && docker-compose exec -T postgres pg_isready -U postgres 2>/dev/null | grep -o "accepting connections" || echo "DOWN"
echo -n "Redis:      " && docker-compose exec -T redis redis-cli ping 2>/dev/null || echo "DOWN"
echo -n "Celery:     " && docker-compose logs celery 2>/dev/null | grep -q "ready" && echo "READY" || echo "DOWN"
echo -n "Frontend:   " && curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 2>/dev/null || echo "DOWN"
```

---

## Troubleshooting Quick Reference

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Backend 500 errors | Database not ready | `docker-compose restart postgres` then `backend` |
| "Connection refused" on :8000 | Backend not started | `docker-compose up backend` |
| Analysis stuck in "pending" | Celery worker down | `docker-compose restart celery` |
| Frontend can't reach API | CORS or wrong API URL | Check `NUXT_PUBLIC_API_URL` in frontend .env |
| pgvector not available | Extension not created | `docker-compose exec postgres psql -U postgres -d geo_platform -c "CREATE EXTENSION IF NOT EXISTS vector;"` |
| Redis connection refused | Redis not started | `docker-compose up redis` |
