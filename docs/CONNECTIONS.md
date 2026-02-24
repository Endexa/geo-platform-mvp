# External Connections & Health Checks

> Run these checks when things break. Each connection includes a command to verify it's alive.

---

## Architecture

```
Browser (Nuxt 3)
  └─> FastAPI Backend (:8000)
        ├─> Supabase PostgreSQL + pgvector (remote)
        ├─> Redis (:6379) — AI response cache + Celery broker + rate limiting
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

## 2. Supabase PostgreSQL (pgvector)

Database is hosted on Supabase. No local PostgreSQL container needed.

```bash
# Test connection from backend
cd backend && source venv/bin/activate
python -c "
from app.core.config import settings
from sqlalchemy import create_engine, text
engine = create_engine(settings.DATABASE_URL, connect_args={'connect_timeout': 10})
with engine.connect() as conn:
    result = conn.execute(text('SELECT version()'))
    print('Connected:', result.fetchone()[0])
"

# Check pgvector extension
python -c "
from app.core.config import settings
from sqlalchemy import create_engine, text
engine = create_engine(settings.DATABASE_URL, connect_args={'connect_timeout': 10})
with engine.connect() as conn:
    result = conn.execute(text(\"SELECT extname FROM pg_extension WHERE extname = 'vector'\"))
    print('pgvector:', result.fetchone())
"

# Check tables
python -c "
from app.core.config import settings
from sqlalchemy import create_engine, text
engine = create_engine(settings.DATABASE_URL, connect_args={'connect_timeout': 10})
with engine.connect() as conn:
    result = conn.execute(text(\"SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename\"))
    for row in result: print(f'  {row[0]}')
"

# Run migrations
cd backend && source venv/bin/activate && alembic upgrade head
```

## 3. Redis

Used for: AI response caching (`AICacheService`), Celery task broker/backend, inbound rate limiting.

```bash
# Via Docker
docker exec geo-redis redis-cli ping
# Expected: PONG

# Check AI cache keys
docker exec geo-redis redis-cli keys "ai_cache:*" | head -5

# Check cache key count
docker exec geo-redis redis-cli dbsize
```

## 4. Celery Worker

Configured in `backend/app/tasks/celery_app.py`. Uses Redis as broker and backend. JSON serialization, late acks, task routing for `audit` and `analysis` queues.

```bash
# If using start.sh — celery runs as a background process
# Check it's alive via ps:
ps aux | grep celery

# If using Docker:
docker logs geo-celery | tail -5
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
echo -n "Supabase:   " && cd backend && source venv/bin/activate && python -c "
from app.core.config import settings; from sqlalchemy import create_engine, text
e = create_engine(settings.DATABASE_URL, connect_args={'connect_timeout': 5})
with e.connect() as c: c.execute(text('SELECT 1')); print('OK')
" 2>/dev/null || echo "DOWN"
echo -n "Redis:      " && docker exec geo-redis redis-cli ping 2>/dev/null || echo "DOWN"
echo -n "Frontend:   " && curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 2>/dev/null || echo "DOWN"
```

---

## Troubleshooting Quick Reference

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Backend 500 errors | Supabase DB unreachable | Check `DATABASE_URL` in `backend/.env`, verify Supabase project is running |
| "Connection refused" on :8000 | Backend not started | Run `./start.sh` or start manually |
| Analysis stuck in "pending" | Celery worker down | Restart celery: `celery -A app.tasks.celery_app worker --loglevel=info` |
| Frontend can't reach API | CORS or wrong API URL | Check `NUXT_PUBLIC_API_BASE` in `frontend/.env` |
| pgvector not available | Extension not enabled | Run SQL on Supabase: `CREATE EXTENSION IF NOT EXISTS vector;` |
| Redis connection refused | Redis container not started | `docker start geo-redis` or `docker run -d --name geo-redis -p 6379:6379 redis:7-alpine` |
| Alembic `%` error | Password with special chars | Already fixed in `alembic/env.py` (escapes `%` as `%%`) |
