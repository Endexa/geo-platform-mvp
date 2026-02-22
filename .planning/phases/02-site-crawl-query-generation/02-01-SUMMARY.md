---
phase: 02-site-crawl-query-generation
plan: 01
subsystem: database, api, services
tags: [sqlalchemy, alembic, pydantic, httpx, beautifulsoup, extruct, robots-txt, crawling]

# Dependency graph
requires:
  - phase: 01-foundation-safety
    provides: "Auth, cost tracking, AuditCostLedger model, Alembic migration chain (001-002)"
provides:
  - "Audit SQLAlchemy model (central pipeline entity)"
  - "AuditQuery model for generated queries"
  - "CrawlerService extracting AI-readiness signals from URLs"
  - "CrawlResult/AIBotAccess Pydantic schemas"
  - "Alembic migration 003 (audits + audit_queries tables)"
  - "FK from audit_cost_ledger to audits"
affects: [02-02, 03-ai-query-dispatch, 04-scoring-engine, 05-api-frontend]

# Tech tracking
tech-stack:
  added: [extruct, w3lib]
  patterns: [JSONB for crawl data storage, AI bot robots.txt checking, content extraction cascade]

key-files:
  created:
    - backend/app/models/audit.py
    - backend/app/models/audit_query.py
    - backend/app/schemas/crawl.py
    - backend/app/schemas/audit.py
    - backend/app/services/crawler_service.py
    - backend/alembic/versions/003_add_audits_and_audit_queries.py
  modified:
    - backend/app/models/__init__.py
    - backend/alembic/env.py
    - backend/requirements.txt

key-decisions:
  - "CrawlerService uses httpx (async) for page fetch, httpx sync for robots.txt"
  - "extruct handles structured data extraction with graceful fallback if unavailable"
  - "Content extraction priority: main > article > largest div > body (follows existing HTMLAnalyzer pattern)"
  - "robots.txt check differentiates between 'no directive' (None) and 'explicitly allowed/blocked' (True/False)"
  - "Migration 003 FK from audit_cost_ledger uses try/except for orphan row safety"

patterns-established:
  - "JSONB column pattern: store complex structured data as JSONB, expose as Pydantic model"
  - "AI bot access pattern: check 8 AI user-agents in robots.txt, return tri-state (allowed/blocked/no-directive)"
  - "Content extraction cascade: main > article > largest-div > body with word-count truncation"
  - "Industry signal detection: schema.org type mapping + keyword frequency heuristic"

requirements-completed: [AUDIT-02]

# Metrics
duration: 4min
completed: 2026-02-22
---

# Phase 2 Plan 1: Site Crawl & Query Generation - Data Models and Crawler Summary

**Audit/AuditQuery SQLAlchemy models with JSONB crawl storage, CrawlerService extracting structured data + robots.txt AI directives + content signals via extruct and BeautifulSoup**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-22T01:02:18Z
- **Completed:** 2026-02-22T01:05:50Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- Audit model established as central pipeline entity with JSONB crawl_data, status enum (7 states), FK to profiles, and relationships to AuditQuery and AuditCostLedger
- AuditQuery model for storing generated queries with category classification (industry, brand_direct, comparison, problem, recommendation)
- CrawlerService with 10 methods extracting: structured data (JSON-LD, OG, microdata), robots.txt AI bot directives (8 bots), content structure, keywords, industry signals, and E-E-A-T authority markers
- Alembic migration 003 creating audits + audit_queries tables and retroactively linking audit_cost_ledger via FK

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Audit and AuditQuery models, Pydantic schemas, and Alembic migration 003** - `7a551417` (feat)
2. **Task 2: Create CrawlerService with httpx, BeautifulSoup, extruct, and robots.txt AI bot check** - `76e57ad9` (feat)

## Files Created/Modified
- `backend/app/models/audit.py` - Audit SQLAlchemy model with AuditStatus enum
- `backend/app/models/audit_query.py` - AuditQuery model for generated queries
- `backend/app/schemas/crawl.py` - CrawlResult and AIBotAccess Pydantic schemas
- `backend/app/schemas/audit.py` - AuditCreate, AuditResponse, AuditDetailResponse, AuditQueryResponse schemas
- `backend/app/services/crawler_service.py` - CrawlerService (412 lines) with full signal extraction
- `backend/alembic/versions/003_add_audits_and_audit_queries.py` - Migration creating tables and FK
- `backend/app/models/__init__.py` - Added Audit, AuditStatus, AuditQuery exports
- `backend/alembic/env.py` - Added Audit, AuditQuery imports for autogenerate
- `backend/requirements.txt` - Added extruct>=0.17.0 and w3lib>=2.1.0

## Decisions Made
- CrawlerService uses httpx AsyncClient for page fetch (async, consistent with FastAPI) and httpx sync Client for robots.txt (simple, one-off check)
- extruct structured data extraction wrapped in try/except with graceful fallback -- extruct can fail on malformed HTML
- robots.txt AI bot check returns tri-state per bot: True (allowed), False (blocked), None (no directive found) -- this distinction matters for scoring
- Migration 003 FK from audit_cost_ledger to audits uses try/except because orphan rows may exist from Phase 1 cost tracking
- Content extraction follows existing HTMLAnalyzer cascade pattern (main > article > largest div > body) for consistency

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Audit and AuditQuery models ready for Plan 02 (query generation with LLM)
- CrawlerService ready to be called from the audit pipeline endpoint
- CrawlResult schema defines the contract for downstream query generation
- Migration 003 ready to run against database with `alembic upgrade head`

## Self-Check: PASSED

- All 7 created files verified present on disk
- Both task commits (7a551417, 76e57ad9) verified in git log

---
*Phase: 02-site-crawl-query-generation*
*Completed: 2026-02-22*
