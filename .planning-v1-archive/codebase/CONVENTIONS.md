# Codebase Conventions

This document captures the coding conventions observed across the GEO Platform MVP codebase. It is derived from reading actual source files and reflects the patterns in use, not aspirational guidelines.

---

## Table of Contents

1. [Python: Naming Conventions](#python-naming-conventions)
2. [Python: Import Organization](#python-import-organization)
3. [Python: Docstrings](#python-docstrings)
4. [Error Handling Patterns](#error-handling-patterns)
5. [Logging Patterns](#logging-patterns)
6. [Database Access Patterns](#database-access-patterns)
7. [API Response Format Conventions](#api-response-format-conventions)
8. [Pydantic Schema Patterns](#pydantic-schema-patterns)
9. [Vue/TypeScript Component Patterns](#vuetypescript-component-patterns)
10. [Measurement Script Conventions](#measurement-script-conventions)

---

## Python: Naming Conventions

### Modules and Files

- Module files use `snake_case`: `brand_voice.py`, `rate_limiter.py`, `geo_datapoints.py`
- Measurement modules use a category prefix + underscore + descriptor: `wi_ssl_certificate.py`, `cnt_word_count.py`, `bv_brand_mentions.py`
- The prefix encodes the measurement category (WI = Web Infrastructure, CNT = Content, BV = Brand Visibility, SEO, UX, COMP, LEG)

### Classes

- Classes use `PascalCase`: `AnalyzerService`, `BrandVoiceService`, `RateLimiter`, `SecurityManager`
- Middleware classes are suffixed with `Middleware`: `SecurityHeadersMiddleware`, `RequestLoggingMiddleware`
- Measurement classes are suffixed with `Measurement`: `SSLCertificateMeasurement`, `WordCountMeasurement`
- Pydantic request models are suffixed with `Request`: `CreateConfigRequest`, `AddRuleRequest`
- Pydantic response models are suffixed with `Response`: `AnalysisResponse`

### Functions and Variables

- Functions and variables use `snake_case`: `get_db`, `run_analysis`, `fetch_content`, `calculate_visibility_score`
- Constants use `UPPER_SNAKE_CASE`: `MAX_REQUEST_SIZE`, `SQL_KEYWORDS`, `ALLOWED_SCHEMES`
- Private methods are prefixed with `_`: `_chunk_text`, `_generate_embedding`, `_calculate_vector_similarity`, `_check_rules`, `_is_internal_link`

### Measurement Codes

- Each measurement has a string code combining category abbreviation and a zero-padded number: `"WI-016"`, `"CNT-006"`, `"CNT-007"`

---

## Python: Import Organization

Imports follow a consistent order across all backend files:

1. **Standard library** imports first
2. **Third-party framework** imports (FastAPI, SQLAlchemy, Pydantic)
3. **Internal application** imports (prefixed `app.`)
4. **Loguru** logger import always last among third-party

Example from `backend/app/api/analysis.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel, HttpUrl
from uuid import UUID
from app.core.database import get_db
from app.models import Analysis, Website, Profile
from app.services.analyzer import AnalyzerService
from app.core.security import get_current_active_user, OrganizationChecker
from app.core.rate_limiter import analysis_rate_limit, standard_rate_limit
from app.core.validators import SecureAnalyzeRequest
from loguru import logger
```

In `geo_data_points/` measurement files, imports follow:

1. Standard library (`typing`, `datetime`, `urllib.parse`)
2. Internal geo package (`geo_data_points.base`, `geo_data_points.utils.*`)
3. `loguru` logger

```python
from typing import Dict, Any
from geo_data_points.base import BaseMeasurement
from geo_data_points.utils.html_parser import HTMLAnalyzer
from loguru import logger
```

---

## Python: Docstrings

### Service and API Layer

API endpoint functions use multi-line docstrings describing purpose, security features, and return format. The security notes are particularly prominent and follow a fixed template:

```python
async def create_analysis(...):
    """
    Initiate a new website analysis.

    **Security Features:**
    - Rate limited: 3 analyses per 5 minutes
    - Input validation: URL and keywords sanitized
    - Audit logged: All requests logged

    **Authentication:** Currently optional for MVP.
    Uncomment dependencies to require authentication.

    Returns analysis_id for polling.
    """
```

### Measurement Classes

Measurement `measure()` methods document the scoring rubric inline with Args/Returns:

```python
async def measure(self, url: str, html: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Measure SSL certificate validity and configuration.

    Scoring:
    - 100: Valid certificate, >90 days until expiration, strong cipher
    - 90: Valid certificate, 30-90 days until expiration
    - 70: Valid certificate, <30 days until expiration (renewal urgent)
    - 50: Valid certificate but weak configuration
    - 0: No HTTPS, expired certificate, or invalid certificate

    Args:
        url: Target URL to analyze
        html: Unused (certificate checked via socket)
        metadata: Unused

    Returns:
        Dict with score (0-100) and detailed comment
    """
```

### Utility Classes

Module-level docstrings describe purpose and notable properties:

```python
"""
HTML Parsing Utilities

Advanced HTML parsing, DOM analysis, and content extraction
optimized for billions of daily operations.
"""
```

Class-level method docstrings are short one-liners for simple getters (`"""Extract all meta tags."""`) and multi-line with Args/Returns for complex methods.

### `BaseMeasurement.__init__`

The constructor documents all parameters using Args block:

```python
def __init__(self, code: str, name: str, description: str, category: str, weight: float = 1.0):
    """
    Initialize measurement with metadata.

    Args:
        code: Unique measurement code (e.g., "WI-001", "CNT-002")
        name: Human-readable measurement name
        description: Detailed description of what this measures
        category: Category (Web Infrastructure, Content, ...)
        weight: Importance weight (0.0-1.0), default 1.0
    """
```

---

## Error Handling Patterns

### API Layer (FastAPI)

The standard pattern is:
1. Query the database for the resource
2. Raise `HTTPException(status_code=404, detail="...")` if not found
3. Validate business rules, raise `HTTPException(status_code=400, detail="...")` for invalid state
4. Catch broad `Exception` in complex operations and re-raise as `HTTPException(status_code=500)`

```python
# From backend/app/api/analysis.py
analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()

if not analysis:
    raise HTTPException(status_code=404, detail="Analysis not found")

if analysis.status != "completed":
    raise HTTPException(status_code=400, detail="Analysis not completed yet")
```

The geo_datapoints API uses a specific re-raise pattern for `HTTPException` inside broad `except` blocks:

```python
# From backend/app/api/geo_datapoints.py
try:
    with get_db_session() as db:
        analysis = db.query(GeoAnalysis).filter(...).first()
        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")
        ...
except HTTPException:
    raise  # Re-raise HTTP exceptions as-is
except Exception as e:
    logger.error(f"Error fetching GEO analysis {analysis_id}: {str(e)}", exc_info=True)
    raise HTTPException(status_code=500, detail="Failed to fetch analysis")
```

### Service Layer

Services use bare `try/except Exception` and update a status field on the model before re-raising:

```python
# From backend/app/services/analyzer.py
def run_analysis(self, analysis_id: UUID, url: str, keywords: list):
    try:
        analysis = self.db.query(Analysis).filter(Analysis.id == analysis_id).first()
        analysis.status = "processing"
        self.db.commit()
        # ... do work ...
    except Exception as e:
        analysis.status = "failed"
        analysis.raw_data = {"error": str(e)}
        self.db.commit()
        raise
```

### Measurement Scripts

Measurement `measure()` methods catch `Exception` and return a zero-score dict with an error message rather than raising:

```python
# From geo_data_points/measurements/wi_ssl_certificate.py
except Exception as e:
    logger.error(f"Error validating SSL certificate for {url}: {str(e)}")
    return {
        'score': 0,
        'comment': f'SSL validation failed: {str(e)}. Ensure site is accessible via HTTPS.'
    }
```

The `BaseMeasurement.execute()` wrapper also catches all exceptions from `measure()` and returns a structured error result:

```python
# From geo_data_points/base.py
except Exception as e:
    error_result = {
        'measurement': self.get_metadata(),
        'execution': {
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        },
        'result': {'score': 0, 'comment': f'Measurement failed: {str(e)}'}
    }
    return error_result
```

### Middleware

The outermost `ErrorSanitizationMiddleware` catches unhandled exceptions and returns sanitized JSON, hiding internal details in production:

```python
# From backend/app/core/middleware.py
if settings.ENVIRONMENT == "production":
    return JSONResponse(status_code=500, content={
        "detail": "An internal error occurred",
        "request_id": getattr(request.state, "request_id", "unknown")
    })
else:
    return JSONResponse(status_code=500, content={
        "detail": "Internal server error",
        "error": str(e),
        "type": type(e).__name__
    })
```

---

## Logging Patterns

### Backend (Loguru)

All backend code imports `loguru`'s `logger` directly:

```python
from loguru import logger
```

Logging levels follow these conventions:

- `logger.info(...)` — normal operation events (request start, record created, operation completed)
- `logger.warning(...)` — recoverable issues, validation failures, rate limit hits
- `logger.error(..., exc_info=True)` — unexpected errors with full stack trace

Common log message patterns:

```python
# Request initiated (with sensitive data stripped — just URL/ID)
logger.info(f"Analysis requested for URL: {request.url}")
logger.info(f"Analysis created with ID: {analysis.id}")

# Warning for business-rule violations
logger.warning(f"Config not found: {config_id}")
logger.warning(f"Rate limit exceeded for {key}. Count: {current_count}/{self.requests}")

# Error with exc_info for debugging
logger.error(f"GEO analysis failed for {url}: {str(e)}", exc_info=True)
```

The `RequestLoggingMiddleware` logs structured data using `extra={}` keyword to attach context fields:

```python
logger.info(
    f"Request started",
    extra={
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "client_ip": request.client.host,
    }
)
```

### geo_data_points (stdlib logging wrapper)

The `geo_data_points` module uses a custom `GeoLogger` class wrapping Python's `logging`:

```python
# From geo_data_points/utils/logging.py
from geo_data_points.utils.logging import get_logger
logger = get_logger("html_parser")

# Domain-specific logging methods
logger.measurement_start(data_point_name, url)
logger.measurement_complete(data_point_name, score, duration_ms)
logger.measurement_error(data_point_name, error)
```

Log output format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`

Log files are stored in `geo_data_points/logs/geo_datapoints_YYYYMMDD.log` with daily rotation.

---

## Database Access Patterns

### Session Management (Backend FastAPI)

Sessions are provided via FastAPI's dependency injection. The `get_db` generator in `backend/app/core/database.py` is the single source of truth:

```python
# From backend/app/core/database.py
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

All API route functions receive `db: Session = Depends(get_db)`. No session is created manually inside routes.

Engine configuration uses connection pooling:

```python
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

### Query Patterns

Standard SQLAlchemy ORM query style (not the newer `select()` style):

```python
# Single record lookup
analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()

# Aggregate
total_analyses = db.query(func.count(Analysis.id)).scalar()
avg_geo_score = db.query(func.avg(Analysis.geo_score)).filter(
    Analysis.status == "completed"
).scalar() or 0

# Count
vector_count = db.query(VoiceVector).filter(VoiceVector.config_id == config_id).count()

# Ordered list with limit
recent_audits = db.query(Analysis).order_by(Analysis.created_at.desc()).limit(5).all()
```

### Write Pattern

All writes follow `add → commit → refresh`:

```python
website = Website(domain=domain)
db.add(website)
db.commit()
db.refresh(website)
```

### geo_data_points Context Manager Session

The `geo_data_points` module uses a context manager pattern separate from the backend:

```python
# From backend/app/api/geo_datapoints.py
with get_db_session() as db:
    analysis = db.query(GeoAnalysis).filter(GeoAnalysis.id == analysis_id).first()
```

### Raw SQL for pgvector

Vector similarity queries use `text()` with raw SQL because SQLAlchemy does not natively understand the pgvector `<=>` operator:

```python
# From backend/app/services/brand_voice.py
query = text(f"""
    SELECT 1 - (embedding <=> '{embedding_str}'::vector) as similarity
    FROM voice_vectors
    WHERE config_id = :config_id
    ORDER BY embedding <=> '{embedding_str}'::vector
    LIMIT 5
""")
results = self.db.execute(query, {"config_id": str(config_id)}).fetchall()
```

### SQLAlchemy Model Conventions

All models inherit from `Base = declarative_base()` imported from `app.core.database`.

Column patterns:
- Primary keys: `UUID(as_uuid=True)` with `default=uuid.uuid4`
- Timestamps: `Column(DateTime, default=datetime.utcnow)` — no timezone awareness
- ForeignKeys use UUID: `Column(UUID(as_uuid=True), ForeignKey("tablename.id"), nullable=False)`
- Optional ForeignKeys use `nullable=True` with a comment explaining the MVP reason
- JSON storage: `Column(JSONB, nullable=True)` for raw data
- Vector storage: `Column(Vector(1536))` from `pgvector.sqlalchemy`

Relationship cascades:
- Child relationships always use `cascade="all, delete-orphan"`

```python
# From backend/app/models/analysis.py
recommendations = relationship("Recommendation", back_populates="analysis", cascade="all, delete-orphan")
```

---

## API Response Format Conventions

### Async Background Job Pattern

Endpoints that trigger background tasks always return immediately with a consistent shape:

```python
return {
    "analysis_id": str(analysis.id),
    "status": "pending",
    "message": "Analysis started. Poll /analysis/{id} for results."
}
```

### Resource Not Found

All 404 responses use `detail` as the key (FastAPI default):

```python
raise HTTPException(status_code=404, detail="Analysis not found")
```

### Pydantic Response Models

When a Pydantic `response_model` is declared, `from_attributes = True` is set in `Config` (Pydantic v1 compatible style):

```python
class AnalysisResponse(BaseModel):
    id: UUID
    status: str
    geo_score: int | None = None
    created_at: str

    class Config:
        from_attributes = True
```

### Manual Dict Serialization

When returning related data, the pattern is a list comprehension building plain dicts with explicit field selection. UUIDs are always converted to `str()`:

```python
return {
    "analysis_id": str(analysis_id),
    "recommendations": [
        {
            "id": str(rec.id),
            "category": rec.category,
            "severity": rec.severity,
            "issue": rec.issue,
            "action_plan": rec.action_plan,
            "impact_score": rec.impact_score,
            "implemented": rec.implemented
        }
        for rec in recommendations
    ]
}
```

### Datetime Serialization

Datetimes are always converted with `.isoformat()`. Nullable datetimes use a conditional:

```python
"created_at": analysis.created_at.isoformat()
"completed_at": analysis.completed_at.isoformat() if analysis.completed_at else None
```

### Score Rounding

Float scores are always rounded to 2 decimal places before returning:

```python
"average_score": round(float(row.average_score), 2)
```

---

## Pydantic Schema Patterns

### Base Models

All request models in the backend inherit from `SecureBaseModel` defined in `backend/app/core/validators.py`:

```python
class SecureBaseModel(BaseModel):
    class Config:
        extra = "forbid"          # Reject unknown fields
        validate_assignment = True
        use_enum_values = True
```

### Validator Pattern

Field validation uses Pydantic v1-style `@validator` decorators (not the v2 `@field_validator`):

```python
class CreateConfigRequest(SecureBaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    description: str | None = Field(None, max_length=500)

    @validator('name', 'description')
    def sanitize_text(cls, v):
        if v:
            return StringSanitizer.sanitize(v, max_length=500)
        return v
```

### Inheritance for Specialization

Secure base schemas are sub-classed to create endpoint-specific models without changing behavior:

```python
class AnalyzeRequest(SecureAnalyzeRequest):
    pass

class CheckVoiceRequest(SecureBrandVoiceCheck):
    pass
```

### Regex-Constrained Fields

Enumerated string values use `pattern=` instead of Python `Enum`:

```python
rule_type: str = Field(..., pattern=r'^(forbidden_word|required_phrase|tone_directive)$')
config_id: str = Field(..., pattern=r'^[a-f0-9-]{36}$')  # UUID format
project_key: str = Field(..., min_length=2, max_length=10, pattern=r'^[A-Z]+$')
```

### Settings Class

Application configuration uses `pydantic_settings.BaseSettings` with `env_file = ".env"` and `case_sensitive = True`:

```python
# From backend/app/core/config.py
class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    OPENAI_API_KEY: str

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

---

## Vue/TypeScript Component Patterns

### Script Setup Style

All Vue files use the Composition API with `<script setup lang="ts">` — no Options API, no `export default defineComponent(...)`.

```typescript
// From frontend/pages/analyze.vue
<script setup lang="ts">
const config = useRuntimeConfig()
const url = ref('')
const analyzing = ref(false)
const results = ref(null)
</script>
```

### Runtime Config for API URL

The backend URL is always accessed through Nuxt's `useRuntimeConfig()`:

```typescript
const config = useRuntimeConfig()
// Usage:
fetch(`${config.public.apiUrl}/api/v1/analysis/analyze`, ...)
```

### State Declarations

Reactive state variables are declared individually with `ref()` at the top of `<script setup>`, before any functions:

```typescript
const loading = ref(true)
const stats = ref({ avgGeoScore: 0, totalAnalyses: 0 })
const recentAudits = ref([])
```

### Data Fetching

Data fetching uses the native `fetch()` API directly — there is no composable layer or `useFetch` abstraction in current pages. `onMounted` is used for dashboard-style data loading:

```typescript
onMounted(async () => {
  try {
    const response = await fetch(`${config.public.apiUrl}/api/v1/dashboard/stats`)
    const data = await response.json()
    stats.value = { avgGeoScore: Math.round(data.avg_geo_score) || 0, ... }
  } catch (error) {
    console.error('Failed to fetch dashboard stats:', error)
  } finally {
    loading.value = false
  }
})
```

### Error Handling in Frontend

Frontend error handling is minimal: errors are logged to `console.error()` and surfaced to users via `alert()`. No toast notification system is used.

```typescript
// From frontend/pages/analyze.vue
} catch (error) {
  console.error('Analysis error:', error)
  alert(error.message || 'Failed to start analysis')
  analyzing.value = false
}
```

### Polling Pattern

Long-running backend operations are polled with `setInterval`. The interval is stored in a variable and explicitly cleared on completion or error:

```typescript
const pollInterval = setInterval(async () => {
  pollAttempts++
  const statusResponse = await fetch(`${config.public.apiUrl}/api/v1/analysis/${analysisId}`)
  const statusData = await statusResponse.json()

  if (statusData.status === 'completed') {
    clearInterval(pollInterval)
    results.value = statusData
  } else if (statusData.status === 'failed') {
    clearInterval(pollInterval)
    alert('Analysis failed.')
  } else if (pollAttempts >= maxPollAttempts) {
    clearInterval(pollInterval)
    alert('Analysis timeout.')
  }
}, 2000)
```

### Layout Usage

All pages wrap their content in `<NuxtLayout name="dashboard">`. The layout provides the sidebar, top bar, and slot for content:

```html
<template>
  <NuxtLayout name="dashboard">
    <div class="space-y-6">
      <!-- page content -->
    </div>
  </NuxtLayout>
</template>
```

### Tailwind CSS Class Conventions

Utility classes use the design system tokens defined in `design-system/endexa-geo-platform/MASTER.md`:

- Cards: `class="card"` (custom utility class)
- Primary buttons: `class="btn-primary"`
- Secondary buttons: `class="btn-secondary"`
- Input fields: `class="input-field"`
- Status badges: `class="badge badge-success"`, `class="badge badge-warning"`, `class="badge badge-danger"`
- Score colors use conditional binding: `:class="getScoreColor(score)"` returning `text-success-600`, `text-warning-600`, or `text-danger-600`

### Icon Usage

Icons come exclusively from `@heroicons/vue/24/outline`. No emoji icons are used in the UI (per design system rules):

```typescript
import { HomeIcon, MagnifyingGlassIcon, LightBulbIcon } from '@heroicons/vue/24/outline'
```

### Computed Properties

Computed values use Vue's `computed()`:

```typescript
const currentPageTitle = computed(() => {
  const item = navigation.find(n => isActive(n.path))
  return item?.label || 'Dashboard'
})
```

---

## Measurement Script Conventions

All measurement scripts in `geo_data_points/measurements/` follow a strict pattern:

### Class Structure

```python
class WordCountMeasurement(BaseMeasurement):
    """One-line class docstring."""

    def __init__(self):
        super().__init__(
            code="CNT-006",
            name="Word Count",
            description="Measures total word count of main content",
            category="Content",
            weight=0.85
        )

    async def measure(self, url: str, html: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Docstring with scoring rubric."""
        try:
            # ... measurement logic ...
            return {'score': score, 'comment': comment}
        except Exception as e:
            logger.error(f"Error measuring word count for {url}: {str(e)}")
            return {'score': 0, 'comment': f'Measurement failed: {str(e)}'}
```

### Module-Level Export

Every measurement file ends with a module-level singleton:

```python
# Export for orchestrator
measurement = SSLCertificateMeasurement()
```

### Return Value Contract

`measure()` always returns a dict with at minimum:
- `score`: `int` in range 0–100
- `comment`: `str` — a human-readable, actionable explanation of the score

Optional keys: `raw_value`, `sub_scores`, `metadata`, `recommendations`, `error`

### Scoring Comments

Comment strings include the level label and actionable next steps, formatted for display:

```python
comment = f'{level}: {word_count:,} words. Excellent depth for AI models!'
# or
comment = f'URGENT: SSL certificate expires in {days_until_expiry} days. Schedule renewal soon.'
```
