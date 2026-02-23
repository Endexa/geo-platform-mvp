---
phase: 10-scale-agency
plan: 01
subsystem: api, database
tags: [sqlalchemy, fastapi, pydantic, alembic, multi-tenant, brand-management]

# Dependency graph
requires:
  - phase: 01-foundation-safety
    provides: Profile model, JWT auth, Alembic migrations
  - phase: 05-audit-experience
    provides: Audit model with domain field, audit API
provides:
  - Brand SQLAlchemy model with user_id FK and unique (user_id, domain) constraint
  - Migration 009 creating brands table and adding brand_id FK to audits
  - BrandService with CRUD + retroactive audit association + domain-based lookup
  - Brand CRUD REST API (6 endpoints, all auth-protected with ownership enforcement)
  - Auto-association of new audits with matching brand by normalized domain
  - normalize_domain() shared utility for consistent domain matching
affects: [10-02, frontend-brands, dashboard-aggregation]

# Tech tracking
tech-stack:
  added: []
  patterns: [domain-normalization, retroactive-association, www-variant-matching]

key-files:
  created:
    - backend/app/models/brand.py
    - backend/alembic/versions/009_add_brands.py
    - backend/app/schemas/brand.py
    - backend/app/services/brand_service.py
    - backend/app/api/brands.py
  modified:
    - backend/app/models/audit.py
    - backend/app/models/__init__.py
    - backend/app/api/audit.py
    - backend/app/main.py

key-decisions:
  - "Domain variant matching: retroactive association matches both 'example.com' and 'www.example.com' since older audits stored raw urlparse.netloc"
  - "Router pattern: brands.py defines its own prefix (/api/v1/brands) following competitors/recommendations pattern, registered with bare include_router()"
  - "normalize_domain in schemas/brand.py: shared between brand creation and audit auto-association for consistency"

patterns-established:
  - "Domain normalization: strip scheme, www., lowercase, strip port via normalize_domain()"
  - "Retroactive association: on brand create, UPDATE existing audits matching domain + user_id"
  - "Service-layer ownership: BrandService.get_brand() enforces user_id match, all API endpoints delegate to it"

requirements-completed: [SCALE-01]

# Metrics
duration: 3min
completed: 2026-02-23
---

# Phase 10 Plan 01: Multi-Brand Model & CRUD Summary

**Brand SQLAlchemy model with CRUD API, migration 009, domain normalization, and auto-association of audits to brands by domain**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-23T00:53:08Z
- **Completed:** 2026-02-23T00:56:39Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- Brand model with UUID PK, user_id FK, unique (user_id, domain) constraint, timestamps
- BrandService with CRUD, retroactive audit association, and domain variant matching
- Brand API with 6 authenticated endpoints all enforcing user ownership
- Audit creation auto-associates with matching brand by normalized domain

## Task Commits

Each task was committed atomically:

1. **Task 1: Brand model, migration, schemas, and model registration** - `66a3c1c7` (feat)
2. **Task 2: BrandService, brand API, auto-association, router registration** - `ade28682` (feat)

## Files Created/Modified
- `backend/app/models/brand.py` - Brand SQLAlchemy model with UUID PK, user_id FK, unique constraint
- `backend/alembic/versions/009_add_brands.py` - Migration creating brands table and adding audits.brand_id
- `backend/app/schemas/brand.py` - Pydantic v2 schemas (BrandCreate, BrandUpdate, BrandResponse, BrandListResponse) + normalize_domain()
- `backend/app/services/brand_service.py` - BrandService with CRUD, retroactive association, domain lookup
- `backend/app/api/brands.py` - Brand CRUD API (6 endpoints: POST, GET list, GET detail, PUT, DELETE, GET audits)
- `backend/app/models/audit.py` - Added nullable brand_id FK column and brand relationship
- `backend/app/models/__init__.py` - Registered Brand model
- `backend/app/api/audit.py` - Added auto-association logic matching brand by normalized domain
- `backend/app/main.py` - Registered brands router

## Decisions Made
- Domain variant matching: retroactive association matches both "example.com" and "www.example.com" since older audits stored raw urlparse.netloc which may include www. prefix
- Router pattern: brands.py defines its own full prefix (/api/v1/brands) following the competitors/recommendations router pattern, registered with bare include_router() in main.py
- normalize_domain placed in schemas/brand.py: shared between brand creation and audit auto-association for consistency (Pitfall 3 from research)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Brand data layer and API complete, ready for Plan 02 (frontend brand management UI)
- Existing audits will be retroactively associated when users create brands
- Auto-association ensures all new audits are linked to brands automatically

---
*Phase: 10-scale-agency*
*Completed: 2026-02-23*
