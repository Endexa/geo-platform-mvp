# Known Incidents & Fixes

> **Search this file FIRST when debugging any error.** If the fix is here, apply it directly. If not, fix the issue, then add a new entry before committing.

---

## Database / PostgreSQL

### pgvector extension not found
**When:** First `docker-compose up`, or after volume reset.
**Root cause:** pgvector extension not created in the database.
**Fix:**
```bash
docker-compose exec postgres psql -U postgres -d geo_platform -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### `sqlalchemy.exc.OperationalError: connection refused`
**When:** Backend starts before PostgreSQL is ready.
**Root cause:** Docker healthcheck hasn't passed yet.
**Fix:** Wait for PostgreSQL healthcheck, or restart:
```bash
docker-compose restart backend
```

---

## Backend / FastAPI

### 401 Unauthorized on all endpoints after Phase 1
**When:** After Phase 1 deployment, all API calls return 401.
**Root cause:** Auth is now enabled on all protected endpoints. A valid JWT token is required.
**Fix:** Register and log in first to get a token:
```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "SecurePass123!"}'
# Use the returned access_token in subsequent requests:
curl http://localhost:8000/api/v1/dashboard/stats \
  -H "Authorization: Bearer <access_token>"
```

### `ImportError: cannot import name 'CryptContext' from 'passlib'`
**When:** Running old code that imports passlib.
**Root cause:** Phase 1 replaced passlib with pwdlib. python-jose replaced with PyJWT.
**Fix:** Use `from pwdlib import PasswordHash` instead of `from passlib.context import CryptContext`. Use `import jwt` instead of `from jose import jwt`.

### CORS errors from frontend
**When:** Frontend shows "Failed to fetch" or network errors.
**Root cause:** CORS origins not matching frontend URL.
**Fix:** Verify `CORS_ORIGINS` in `backend/app/core/config.py` includes `http://localhost:3000`.

### Analysis stuck in "pending" forever
**When:** After starting an analysis, status never changes to "completed".
**Root cause:** Celery worker not running or crashed.
**Fix:**
```bash
docker-compose logs celery     # Check for errors
docker-compose restart celery  # Restart worker
```

### OpenAI API 401 Unauthorized
**When:** Generating recommendations (when integrated).
**Root cause:** Invalid or missing `OPENAI_API_KEY`.
**Fix:** Verify key in `.env`:
```bash
curl https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY"
```

---

## Frontend / Nuxt

### `npm run dev` fails with module resolution errors
**When:** After pulling new changes or switching branches.
**Root cause:** Stale node_modules or .nuxt cache.
**Fix:**
```bash
cd frontend
rm -rf node_modules .nuxt
npm install
npm run dev
```

---

## Docker / Infrastructure

### Port already in use (5432, 6379, 8000, 3000)
**When:** `docker-compose up` fails with "port already allocated".
**Root cause:** Another process or previous docker run using the port.
**Fix:**
```bash
# Find what's using the port
lsof -i :8000
# Kill it, or stop previous containers
docker-compose down
```

### `docker-compose up --build` very slow
**When:** First build or after Dockerfile changes.
**Root cause:** No Docker cache, downloading all dependencies.
**Fix:** This is normal for first build. Subsequent builds use cache. If consistently slow, check if `.dockerignore` excludes `node_modules/`, `venv/`, `__pycache__/`.

---

## GEO Data Points

### Measurement script returns score 0 for everything
**When:** Running orchestrator on any URL.
**Root cause:** Most scripts (103/108) are stubs that return 0. Only 5 are fully implemented.
**Fix:** This is expected for now. See `docs/BACKLOG.md` Priority 2 for implementation plan.

### HTTP timeout when crawling URL
**When:** Analyzing a URL that's slow or blocks bots.
**Root cause:** Target site rate-limiting or blocking requests.
**Fix:** Check `GEO_REQUEST_TIMEOUT` in `.env` (default 10s). Some sites block automated requests — test with a different URL first.

<!-- Add new incidents above this line, under the appropriate category -->
