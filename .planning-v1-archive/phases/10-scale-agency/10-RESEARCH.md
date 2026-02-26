# Phase 10: Scale & Agency - Research

**Researched:** 2026-02-23
**Domain:** Multi-brand management, agency-level data isolation, cross-brand comparison dashboards
**Confidence:** HIGH

## Summary

Phase 10 adds multi-brand management for agency users: a Brand model that groups audits under named brands, CRUD API endpoints for brand management, and a cross-brand comparison dashboard. The technical challenge is modest because the existing codebase already has per-user data isolation via `user_id` on the Audit model and an Organization model with tier-based access control. The core work is introducing a `brands` table that sits between users and audits, adding an optional `brand_id` FK to the existing `audits` table, and building a multi-brand aggregation API that reuses the existing `DashboardService` logic.

The approach is "shared database, shared schema with FK-based grouping" -- the simplest multi-tenant pattern that fits this codebase. Each brand belongs to a user (and optionally an organization). Audits gain an optional `brand_id` column. Existing single-brand users are unaffected -- their audits simply have `brand_id=NULL` and continue working exactly as before. Agency users create brands, associate audits with brands, and get a cross-brand dashboard view.

**Primary recommendation:** Add a `brands` table with `user_id` FK, add optional `brand_id` FK to `audits` table, build brand CRUD API + multi-brand dashboard API, and build a frontend brands page with cross-brand comparison view. Use the existing `DashboardService.get_overview()` pattern for per-brand aggregation. Do NOT implement PostgreSQL Row-Level Security, schema-per-tenant, or database-per-tenant -- all are overkill for this use case where simple FK-based ownership with WHERE clauses is sufficient.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SCALE-01 | Agency users can create and manage multiple brands under one account, each with separate audit history and tracking | Brand model with user_id FK, brand CRUD API, per-brand audit association via brand_id FK on audits table, brand-specific audit history endpoint |
| SCALE-02 | Multi-brand view shows a summary dashboard comparing scores across all managed brands | Multi-brand aggregation endpoint that calls existing DashboardService per-brand, BrandComparison frontend component with score comparison table/chart |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | existing | Brand model + migration | Already the ORM for all models in the project |
| Alembic | existing | Migration 009 for brands table + audits FK | Already used for all 8 previous migrations |
| FastAPI | existing | Brand CRUD + multi-brand dashboard endpoints | Already the API framework |
| Pydantic v2 | existing | Brand request/response schemas | Already used for all API schemas |
| Vue 3 / Nuxt 3 | existing | Brands page + multi-brand dashboard | Already the frontend framework |
| Chart.js + vue-chartjs | existing | Cross-brand comparison bar chart | Already installed (used in CompetitorRadar, TrendChart) |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Heroicons | existing | Brand management UI icons (BuildingOfficeIcon) | Sidebar nav + page icons |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| FK-based brand ownership | PostgreSQL Row-Level Security | RLS adds DB-level isolation but requires separate DB users, session variable management, and is overkill for a simple brand-grouping feature where application-level WHERE clauses are sufficient and consistent with the rest of the codebase |
| Optional brand_id on audits | Mandatory brand_id (require every audit to have a brand) | Mandatory brand_id breaks backward compatibility -- existing audits have no brand. Optional FK is simpler, non-breaking, and existing users can use the app without ever creating a brand |
| Per-brand separate dashboard calls | Single aggregation query joining brands+audits | Multiple dashboard calls (one per brand) are simpler to implement and reuse existing DashboardService logic without needing a complex cross-table aggregation query |

**Installation:**
```bash
# No new dependencies needed -- everything is already installed
```

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
├── models/
│   └── brand.py              # Brand SQLAlchemy model
├── schemas/
│   └── brand.py              # Brand Pydantic schemas (CRUD + multi-brand dashboard)
├── api/
│   └── brands.py             # Brand CRUD + multi-brand dashboard endpoints
├── services/
│   └── brand_service.py      # Brand management + multi-brand aggregation logic
└── alembic/versions/
    └── 009_add_brands.py     # Migration: brands table + audits.brand_id FK

frontend/
├── pages/
│   └── brands.vue            # Brand management + multi-brand dashboard page
├── components/
│   ├── BrandCard.vue         # Individual brand summary card
│   └── BrandComparison.vue   # Cross-brand score comparison chart
└── layouts/
    └── dashboard.vue         # Add "Brands" nav item
```

### Pattern 1: Brand Model with Optional FK on Audits
**What:** A `brands` table with `user_id` FK. The `audits` table gets an optional `brand_id` FK. Brands belong to users; audits optionally belong to brands.
**When to use:** When adding a grouping concept on top of existing user-owned records without breaking backward compatibility.
**Example:**
```python
# backend/app/models/brand.py
class Brand(Base):
    __tablename__ = "brands"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False, index=True)
    name = Column(String, nullable=False)           # Display name: "Acme Corp"
    url = Column(String, nullable=False)             # Primary URL: "https://acme.com"
    domain = Column(String, nullable=False)          # Extracted domain: "acme.com"
    description = Column(String, nullable=True)      # Optional notes
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("Profile", backref="brands")
    audits = relationship("Audit", back_populates="brand", order_by="Audit.created_at.desc()")
```

### Pattern 2: Audit-to-Brand Association via Domain Matching
**What:** When creating an audit, if the user has brands, automatically associate the audit with the matching brand based on domain.
**When to use:** To provide seamless brand association without requiring users to manually select a brand every time they run an audit.
**Example:**
```python
# In audit creation endpoint
def create_audit(request: AuditCreate, ...):
    domain = urlparse(request.url).netloc
    # Auto-associate with matching brand
    brand = db.query(Brand).filter(
        Brand.user_id == current_user.id,
        Brand.domain == domain,
    ).first()
    audit = Audit(
        user_id=current_user.id,
        brand_id=brand.id if brand else None,
        url=request.url,
        domain=domain,
    )
```

### Pattern 3: Multi-Brand Dashboard via Per-Brand Aggregation
**What:** The multi-brand dashboard endpoint iterates over the user's brands, finds the latest completed audit per brand, and calls existing DashboardService.get_overview() for each.
**When to use:** When cross-brand comparison data needs to be assembled from existing per-audit aggregation logic.
**Example:**
```python
# In brand_service.py
def get_multi_brand_overview(self, user_id: str) -> list[dict]:
    brands = self.db.query(Brand).filter(Brand.user_id == user_id).all()
    summaries = []
    for brand in brands:
        latest_audit = (
            self.db.query(Audit)
            .filter(Audit.brand_id == brand.id, Audit.status == "completed")
            .order_by(Audit.created_at.desc())
            .first()
        )
        if latest_audit:
            svc = DashboardService(self.db)
            overview = svc.get_overview(str(latest_audit.id), user_id)
            summaries.append({
                "brand_id": str(brand.id),
                "brand_name": brand.name,
                "brand_url": brand.url,
                "latest_audit_id": str(latest_audit.id),
                "combined_geo_score": overview["combined_geo_score"],
                "visibility_score": overview["visibility_score"],
                "optimization_score": overview["optimization_score"],
                "top_issues_count": len(overview["top_issues"]),
                "mention_count": overview["mention_count"],
                "completed_at": overview["completed_at"],
            })
    return summaries
```

### Pattern 4: Backward-Compatible Migration
**What:** Migration adds `brands` table and adds optional `brand_id` column to `audits` with no default -- existing rows simply have NULL brand_id.
**When to use:** When extending an existing table without breaking existing records.
**Example:**
```python
# 009_add_brands.py
def upgrade() -> None:
    op.create_table("brands", ...)
    op.add_column("audits",
        sa.Column("brand_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("brands.id"), nullable=True))
    op.create_index("ix_audits_brand_id", "audits", ["brand_id"])
```

### Anti-Patterns to Avoid
- **Mandatory brand_id on audits:** Would break all existing audits and force users to create a brand before running their first audit. Keep it optional.
- **Separate database/schema per brand:** Massive over-engineering for a simple grouping concept. The project has 18 models in one schema -- adding brand-level isolation at the DB level is not justified.
- **Duplicating DashboardService logic for brands:** Reuse existing `get_overview()` by calling it per-brand. Don't build a parallel aggregation pipeline.
- **Brand-scoped URLs on every existing endpoint:** Don't refactor existing endpoints (audit, recommendations, competitors, dashboard) to accept brand_id. Instead, add new brand-specific endpoints and let the existing per-audit endpoints work unchanged.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Domain extraction from URL | Custom regex parser | `urllib.parse.urlparse().netloc` | Already used in audit.py create_audit endpoint, handles all edge cases |
| Cross-brand score comparison chart | Custom canvas rendering | Chart.js Bar chart via vue-chartjs | Already installed, consistent with existing TrendChart and CompetitorRadar |
| Brand name uniqueness per user | Application-level unique check | SQLAlchemy UniqueConstraint on (user_id, domain) | DB-level enforcement prevents race conditions |

**Key insight:** This phase introduces no new external dependencies. Every library needed is already installed and in use. The core challenge is data modeling and API design, not technology selection.

## Common Pitfalls

### Pitfall 1: Breaking Existing Single-Brand Users
**What goes wrong:** Making brand_id required on audits breaks all existing functionality. Users who don't need multi-brand management are forced into the brand workflow.
**Why it happens:** Overengineering for the agency use case at the expense of simplicity.
**How to avoid:** Keep `brand_id` nullable on `audits`. Existing endpoints work unchanged. Brand-related features are additive -- users who never create a brand never encounter them.
**Warning signs:** Any migration that adds a NOT NULL constraint on audits.brand_id without a default.

### Pitfall 2: N+1 Queries in Multi-Brand Dashboard
**What goes wrong:** Loading 10+ brands, each calling `DashboardService.get_overview()` which runs 5+ queries per brand = 50+ queries per dashboard load.
**Why it happens:** Naively iterating over brands and calling full per-audit aggregation.
**How to avoid:** For the multi-brand summary, only fetch the lightweight data needed (scores, dates) directly from the Audit + VisibilityScore tables. Reserve the full `get_overview()` call for when the user clicks into a specific brand's detailed dashboard.
**Warning signs:** Dashboard load time > 2 seconds with 5+ brands.

### Pitfall 3: Domain Mismatch Between Brand URL and Audit URL
**What goes wrong:** User creates brand with URL "https://www.acme.com" but runs audit on "https://acme.com" (without www). Auto-association fails because domains don't match.
**Why it happens:** Domain normalization inconsistency.
**How to avoid:** Normalize domains at both brand creation and audit creation time: strip www prefix, lowercase, strip trailing slashes. Use the same normalization function in both places.
**Warning signs:** Audits that should belong to a brand showing as unassociated.

### Pitfall 4: Missing User Ownership Checks on Brand Endpoints
**What goes wrong:** User A can view/edit/delete User B's brands because the endpoint only checks brand_id existence, not brand.user_id == current_user.id.
**Why it happens:** Standard OWASP broken access control -- forgetting the ownership filter.
**How to avoid:** Every brand endpoint MUST filter by `Brand.user_id == current_user.id`. Use a shared `_get_brand_for_user()` helper like `_get_audit_for_user()` in audit.py.
**Warning signs:** Any brand query that uses `Brand.id == brand_id` without also filtering `Brand.user_id == current_user.id`.

### Pitfall 5: Sidebar Navigation Clutter
**What goes wrong:** Adding "Brands" to the sidebar creates visual clutter, especially for users who only manage one brand.
**Why it happens:** Adding navigation items without considering the single-brand user experience.
**How to avoid:** Add "Brands" to the sidebar (always visible since it's a core navigation path), but make the brands page show a clear empty state with a CTA for users who haven't created brands yet. The multi-brand dashboard only appears when 2+ brands exist.
**Warning signs:** Users confused about whether they need to create a brand to use the app.

## Code Examples

Verified patterns from the existing codebase (these show the established conventions to follow):

### Model Definition Pattern (from audit.py)
```python
# Source: backend/app/models/audit.py
class Audit(Base):
    __tablename__ = "audits"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False)
    # ...
```

### Ownership Check Pattern (from audit.py API)
```python
# Source: backend/app/api/audit.py
def _get_audit_for_user(audit_id: str, db: Session, current_user: Profile) -> Audit:
    audit = db.query(Audit).filter(Audit.id == audit_id).first()
    if not audit or audit.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found")
    return audit
```

### Manual Migration Pattern (from 008 migration)
```python
# Source: backend/alembic/versions/008_add_recommendations_sentiments_content_gaps.py
revision: str = "009"
down_revision: Union[str, None] = "008"

def upgrade() -> None:
    op.create_table("brands", ...)
    op.add_column("audits", sa.Column("brand_id", ..., nullable=True))
    op.create_index(...)
```

### Router Registration Pattern (from main.py)
```python
# Source: backend/app/main.py
# Existing pattern: some routers have prefix in main.py, some in the router itself
app.include_router(
    brands.router,
    prefix=f"{settings.API_V1_PREFIX}/brands",
    tags=["brands"],
)
```

### Dashboard Service Reuse Pattern (from dashboard_service.py)
```python
# Source: backend/app/services/dashboard_service.py
# get_overview() takes audit_id + user_id, returns full aggregated dict
# For multi-brand: call this per brand's latest audit
service = DashboardService(db)
data = service.get_overview(audit_id, str(current_user.id))
```

### Sidebar Navigation Pattern (from layouts/dashboard.vue)
```typescript
// Source: frontend/layouts/dashboard.vue
const navigation = [
  { path: '/dashboard', label: 'Dashboard', icon: HomeIcon },
  { path: '/analyze', label: 'Analyze', icon: MagnifyingGlassIcon },
  // ... add { path: '/brands', label: 'Brands', icon: BuildingOfficeIcon }
]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Schema-per-tenant isolation | Shared schema with FK-based grouping + RLS optional | 2024-2025 | Most SaaS apps use shared schema for simplicity; RLS for compliance-heavy sectors |
| Separate brand databases | Single database with brand_id column | Industry standard | Reduces operational complexity dramatically |
| Manual brand-audit association | Auto-association by domain matching | Common UX pattern | Reduces friction for agency users managing many brands |

**Deprecated/outdated:**
- Database-per-tenant: Only relevant for strict regulatory compliance (healthcare, finance). Not applicable here.
- Schema-per-tenant: Adds migration complexity (must migrate N schemas). Not justified for this use case.

## Open Questions

1. **Brand limit per user**
   - What we know: Agency users need multiple brands. Free-tier users might also want multiple brands.
   - What's unclear: Should there be a per-tier brand limit (e.g., free=1, pro=10, enterprise=unlimited)?
   - Recommendation: Add a `max_brands` config setting (default unlimited for v1). Can be tier-gated later via the existing OrganizationChecker pattern. Don't over-constrain in the first implementation.

2. **Retroactive brand association for existing audits**
   - What we know: Existing audits have `brand_id=NULL`. When a user creates a brand with domain "acme.com", their old audits for that domain are not auto-associated.
   - What's unclear: Should brand creation retroactively associate existing audits?
   - Recommendation: Yes -- when a brand is created, run a one-time query to associate all existing audits with matching domain. This makes the brands feature immediately useful by showing audit history. Implement as part of the brand creation flow.

3. **Organization vs User ownership**
   - What we know: Profile model has `org_id` FK to Organization. Organization has `subscription_tier`. Brands could belong to either users or organizations.
   - What's unclear: Should brands belong to the organization (shared across org members) or to individual users?
   - Recommendation: Brands belong to `user_id` for v1. This is simpler and matches how audits currently work (audits.user_id). Organization-level brand sharing (multiple org members can see the same brands) is a v2 feature that would require role-based brand access control.

## Sources

### Primary (HIGH confidence)
- Existing codebase analysis: All model patterns, migration patterns, API patterns, and service patterns verified by reading actual source files
- `backend/app/models/audit.py` -- Audit model with user_id FK (the pattern Brand will follow)
- `backend/app/models/profile.py` -- Profile model with org_id FK (existing user-org relationship)
- `backend/app/models/organization.py` -- Organization model with subscription_tier (existing tier system)
- `backend/app/services/dashboard_service.py` -- DashboardService.get_overview() (will be reused for per-brand aggregation)
- `backend/app/api/audit.py` -- Ownership check pattern (_get_audit_for_user) and audit creation pattern
- `backend/app/core/security.py` -- RoleChecker, OrganizationChecker patterns for access control
- `backend/alembic/versions/008_*.py` -- Latest migration pattern to follow

### Secondary (MEDIUM confidence)
- [Crunchy Data: Designing Your Postgres Database for Multi-tenancy](https://www.crunchydata.com/blog/designing-your-postgres-database-for-multi-tenancy) -- Confirms shared-schema approach is standard for most SaaS
- [Crunchy Data: Row Level Security for Tenants in Postgres](https://www.crunchydata.com/blog/row-level-security-for-tenants-in-postgres) -- Confirms RLS is optional for non-compliance use cases
- [FastAPI Row Security](https://adityamattos.com/multi-tenancy-in-python-fastapi-and-sqlalchemy-using-postgres-row-level-security) -- FastAPI + SQLAlchemy RLS pattern (documented but NOT recommended for this project)
- [Multi-Tenant Database Architecture Patterns](https://www.bytebase.com/blog/multi-tenant-database-architecture-patterns-explained/) -- Comparison of shared-schema vs separate-schema vs separate-DB approaches
- [Multi-Tenant Architecture Guide](https://bix-tech.com/multi-tenant-architecture-the-complete-guide-for-modern-saas-and-analytics-platforms-2/) -- Agency dashboard patterns and tenant-scoped branding

### Tertiary (LOW confidence)
- None -- all findings are based on codebase analysis and verified web sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - No new libraries needed, all patterns already established in codebase
- Architecture: HIGH - Simple FK-based grouping pattern, verified against existing model conventions
- Pitfalls: HIGH - Identified from codebase analysis and industry patterns, all concrete and preventable

**Research date:** 2026-02-23
**Valid until:** 2026-03-23 (stable domain -- no fast-moving dependencies)
