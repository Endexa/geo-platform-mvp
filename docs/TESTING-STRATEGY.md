# Testing Strategy

> Defines what to test and when, organized by tiers and change type.

---

## Testing Tiers

### Tier 0 — Lint + Build (every change)

```bash
cd frontend && npm run build    # Must pass
cd backend && python -m py_compile app/main.py  # Syntax check
```

**When:** After every code change. Non-negotiable.

### Tier 1 — Unit Tests (during development)

```bash
# Backend
cd backend && pytest tests/test_<module>.py -v

# Frontend
cd frontend && npm run test -- --filter <component>
```

**When:** After implementing a feature or fixing a bug. Run only the tests relevant to your change.

### Tier 2 — Integration Tests (before merge)

```bash
# API endpoints
cd backend && pytest tests/integration/ -v

# Measurement scripts
cd geo_data_points && python -m pytest tests/ -v

# Full orchestrator run
python geo_data_points/orchestrator/run_all.py --url https://example.com --modules wi
```

**When:** Before merging to main. Tests that hit real services or databases.

### Tier 3 — E2E (before production deploy)

```bash
# Docker stack must be running
docker-compose up --build

# Full user flow test
curl -X POST http://localhost:8000/api/v1/analysis/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "keywords": ["test"]}' | jq

# Poll until complete
curl http://localhost:8000/api/v1/analysis/<id> | jq '.status'
```

**When:** Before deploying to production. Full stack must be up.

---

## Scope Matrix

| Change Type | Tier 0 | Tier 1 | Tier 2 | Tier 3 |
|------------|--------|--------|--------|--------|
| Measurement script (geo_data_points) | Build | Run that script | Orchestrator with module | - |
| API endpoint (backend/app/api/) | Build | pytest for endpoint | curl test | Full flow |
| Service logic (backend/app/services/) | Build | pytest for service | API integration | - |
| Frontend page (frontend/pages/) | Build | - | - | Manual check |
| Frontend component (frontend/components/) | Build | Component test | - | - |
| Database schema (models/ or migrations) | Build | - | `alembic upgrade head` | Full flow |
| Docker config | - | - | `docker-compose up --build` | Full flow |
| Middleware (backend/app/core/middleware.py) | Build | pytest | curl with headers | - |
| Config change (.env, config.py) | Build | - | Docker restart | Health checks |

---

## When to Add New Tests

**Mandatory:**
- New API endpoint → pytest test for happy path + error case
- New measurement script → test with known URL that exercises the measurement
- Bug fix → test that reproduces the bug and verifies the fix

**Recommended:**
- New service method → unit test with mocked dependencies
- Complex business logic → parametrized test with edge cases

**Not required:**
- Frontend styling changes
- Documentation changes
- Config tweaks

---

## Performance Benchmarks

| Operation | Expected Time |
|-----------|--------------|
| Dashboard load | < 500ms |
| Start analysis (return analysis_id) | < 200ms |
| Analysis completion | 10-30s |
| Single measurement script | < 5s |
| Full 108-point orchestrator | < 120s |
| Recommendation generation | 5-15s (when LLM integrated) |
| Brand voice check | 2-5s |
