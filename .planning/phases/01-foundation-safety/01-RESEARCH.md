# Phase 1: Foundation & Safety - Research

**Researched:** 2026-02-22
**Domain:** Authentication, cost tracking, response caching, outbound rate limiting (FastAPI + Redis + PostgreSQL)
**Confidence:** HIGH

## Summary

Phase 1 secures the platform before any AI API integration code is written. The existing codebase has substantial scaffolding: JWT auth code exists but is disabled (commented-out `Depends` on all endpoints), Redis is in docker-compose and used for inbound rate limiting, and the `security.py` module has working password hashing and token creation. However, several components need fixing or building from scratch: there are no auth endpoints (register/login), no cost tracking model or service, no AI response caching layer, no outbound rate limiting (the existing rate limiter only handles inbound requests), no Celery task infrastructure (the `tasks/` directory is empty), and no Alembic migrations.

Critical dependency updates are required: `python-jose` is abandoned (last release 2021, broken on Python 3.13) and must be replaced with `PyJWT` per official FastAPI documentation. `passlib` is deprecated in Python 3.11+ due to `crypt` module removal and should be replaced with `pwdlib`. The `declarative_base()` import path is deprecated in SQLAlchemy 2.0. Six CONCERNS.md items (H-11 disabled auth, M-23 committed .env, M-20 rate limiter fails open, M-22 BackgroundTasks instead of Celery, H-9 random number fallbacks, H-4 dual ORM) directly affect this phase.

**Primary recommendation:** Fix dependency issues (PyJWT, pwdlib, SQLAlchemy imports) first, then build auth endpoints, cost tracking model, Redis caching service, and outbound rate limiter as four vertical slices -- each with its own model, service, and test coverage.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FOUND-01 | User authentication with JWT (enable existing scaffolding) | Auth scaffolding exists in `security.py` with `SecurityManager`, `get_current_user`, `get_current_active_user`. Must: replace `python-jose` with `PyJWT`, replace `passlib` with `pwdlib`, add `password_hash` column to Profile model, create register/login endpoints, uncomment `Depends(get_current_active_user)` on all protected routes. See Architecture Patterns: Auth Flow. |
| FOUND-02 | Per-audit cost tracking with budget caps to prevent API cost explosion | No cost tracking exists. Must create: `AuditCostLedger` model (tracks per-request cost entries), `AuditBudget` model or config (per-audit cap), `CostTrackingService` that uses LiteLLM's `response._hidden_params["response_cost"]` and `completion_cost()`. Budget check runs before each AI call. See Architecture Patterns: Cost Tracking. |
| FOUND-03 | Redis caching for AI engine responses (24h TTL) | Redis is available (docker-compose, `redis==5.0.1` in requirements). Existing rate limiter uses sync `redis.Redis`. Must build: `AICacheService` with `redis.asyncio` for async operations, cache key = hash of `(model, messages, temperature)`, 24h TTL (86400 seconds), JSON serialization of responses. See Architecture Patterns: Response Caching. |
| FOUND-04 | Outbound rate limiting per AI engine API | Existing `rate_limiter.py` only handles inbound request limiting. Must build: per-provider `asyncio.Semaphore` (concurrency cap) + token bucket or sliding window (RPM cap), configurable per engine (OpenAI, Anthropic, Perplexity have different limits), back-pressure that blocks callers until capacity is available. See Architecture Patterns: Outbound Rate Limiting. |
</phase_requirements>

## Standard Stack

### Core (Already in Project)

| Library | Current Version | Target Version | Purpose | Notes |
|---------|----------------|----------------|---------|-------|
| FastAPI | 0.109.0 | 0.109.0 (keep) | Web framework | Stable, no upgrade needed |
| SQLAlchemy | 2.0.25 | 2.0.25 (keep) | ORM | Fix deprecated `declarative_base` import |
| Pydantic | 2.5.3 | 2.5.3 (keep) | Validation | Stable |
| pydantic-settings | 2.1.0 | 2.1.0 (keep) | Config | Stable |
| Redis | 5.0.1 | 5.0.1 (keep) | Cache + rate limiting + Celery broker | Add `redis.asyncio` usage |
| Celery | 5.3.4 | 5.3.4 (keep) | Task queue | Needs initialization (`celery_app.py`) |
| Loguru | 0.7.2 | 0.7.2 (keep) | Logging | Stable |

### Must Replace

| Library | Current | Replace With | Version | Why |
|---------|---------|-------------|---------|-----|
| python-jose | 3.3.0 | PyJWT | 2.10.x | python-jose abandoned since 2021, incompatible with Python >= 3.13. FastAPI docs officially switched to PyJWT. |
| passlib | 1.7.4 | pwdlib[bcrypt] | 0.2.x | passlib deprecated in Python 3.11+ (crypt module removed in 3.13). FastAPI docs switched to pwdlib. |

### Must Add

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| alembic | 1.13.1 (already in requirements) | DB migrations | Every schema change. Currently no alembic.ini or migrations dir. |

### Not Needed for Phase 1

| Library | Why Not Now |
|---------|------------|
| LiteLLM | Phase 1 builds the cost tracking *infrastructure* (models, service interface), but no actual AI calls happen until Phase 3. LiteLLM is already in requirements for later. |
| httpx | Already in requirements. Will be used in Phase 3 for direct API calls. |

**Installation changes:**
```bash
# Remove
pip uninstall python-jose passlib

# Add
pip install PyJWT pwdlib[bcrypt]

# requirements.txt changes:
# python-jose[cryptography]==3.3.0  ->  PyJWT==2.10.1
# passlib[bcrypt]==1.7.4            ->  pwdlib[bcrypt]==0.2.1
```

## Architecture Patterns

### Recommended Project Structure (Phase 1 additions)

```
backend/
├── alembic/                     # NEW: migrations directory
│   ├── versions/                # Migration scripts
│   └── env.py                   # Alembic environment config
├── alembic.ini                  # NEW: Alembic config
├── app/
│   ├── api/
│   │   ├── auth.py              # NEW: register, login, refresh endpoints
│   │   ├── analysis.py          # MODIFY: uncomment auth Depends
│   │   ├── brand_voice.py       # MODIFY: uncomment auth Depends
│   │   └── ...
│   ├── core/
│   │   ├── security.py          # MODIFY: PyJWT + pwdlib migration
│   │   ├── config.py            # MODIFY: add cost/cache config vars
│   │   ├── database.py          # MODIFY: fix declarative_base import
│   │   └── rate_limiter.py      # MODIFY: add outbound rate limiter
│   ├── models/
│   │   ├── profile.py           # MODIFY: add email, password_hash columns
│   │   ├── audit_cost.py        # NEW: cost tracking model
│   │   └── ...
│   ├── schemas/
│   │   ├── auth.py              # NEW: register/login request/response schemas
│   │   └── ...
│   ├── services/
│   │   ├── auth_service.py      # NEW: registration, login logic
│   │   ├── cost_service.py      # NEW: cost tracking, budget checks
│   │   ├── cache_service.py     # NEW: Redis AI response caching
│   │   └── ...
│   └── tasks/
│       ├── __init__.py          # NEW
│       └── celery_app.py        # NEW: Celery application config
```

### Pattern 1: Auth Flow (FOUND-01)

**What:** Email/password registration and JWT login with existing SecurityManager
**When to use:** All protected endpoints

The existing `security.py` has most of the JWT infrastructure. The migration path is:

1. Replace `from jose import JWTError, jwt` with `import jwt` and `from jwt.exceptions import InvalidTokenError`
2. Replace `pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")` with `from pwdlib import PasswordHash; pwd_context = PasswordHash.recommended()`
3. Add email + password_hash columns to Profile model
4. Create auth router with register/login/refresh endpoints
5. Uncomment `Depends(get_current_active_user)` on all protected routes

**Example - PyJWT token creation (replacing python-jose):**
```python
# Source: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
import jwt
from jwt.exceptions import InvalidTokenError
from datetime import datetime, timedelta, timezone

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=30))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid credentials")
```

**Example - pwdlib password hashing (replacing passlib):**
```python
# Source: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()

def hash_password(password: str) -> str:
    return password_hash.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)
```

**Example - Register endpoint:**
```python
@router.post("/register", response_model=TokenResponse)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    # Check duplicate email
    existing = db.query(Profile).filter(Profile.email == request.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create user with hashed password
    user = Profile(
        id=uuid.uuid4(),
        email=request.email,
        password_hash=hash_password(request.password),
        full_name=request.full_name,
    )
    db.add(user)
    db.commit()

    # Return tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}
```

### Pattern 2: Cost Tracking (FOUND-02)

**What:** Track every AI API call's cost and enforce per-audit budget caps
**When to use:** Before and after every AI engine call (Phase 3+, but model and service built in Phase 1)

```python
# Model: audit_cost.py
class AuditCostLedger(Base):
    __tablename__ = "audit_cost_ledger"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id = Column(UUID(as_uuid=True), ForeignKey("audits.id"), nullable=False, index=True)
    engine = Column(String, nullable=False)        # "openai", "anthropic", "perplexity"
    model = Column(String, nullable=False)          # "gpt-4o", "claude-sonnet-4", "sonar-pro"
    prompt_tokens = Column(Integer, nullable=False)
    completion_tokens = Column(Integer, nullable=False)
    cost_usd = Column(Numeric(10, 6), nullable=False)  # 6 decimal places for sub-cent costs
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# Service: cost_service.py
class CostTrackingService:
    DEFAULT_BUDGET_USD = 1.00  # $1 per audit default cap

    def __init__(self, db: Session):
        self.db = db

    def get_audit_spend(self, audit_id: UUID) -> Decimal:
        """Sum all cost entries for an audit."""
        result = self.db.query(func.sum(AuditCostLedger.cost_usd)).filter(
            AuditCostLedger.audit_id == audit_id
        ).scalar()
        return result or Decimal("0")

    def check_budget(self, audit_id: UUID, budget_usd: Decimal | None = None) -> bool:
        """Returns True if audit is within budget."""
        budget = budget_usd or Decimal(str(self.DEFAULT_BUDGET_USD))
        return self.get_audit_spend(audit_id) < budget

    def record_cost(self, audit_id: UUID, engine: str, model: str,
                    prompt_tokens: int, completion_tokens: int, cost_usd: Decimal):
        """Record a single AI API call cost."""
        entry = AuditCostLedger(
            audit_id=audit_id, engine=engine, model=model,
            prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
            cost_usd=cost_usd,
        )
        self.db.add(entry)
        self.db.commit()
```

**LiteLLM cost extraction (used in Phase 3, interface designed in Phase 1):**
```python
# Source: https://docs.litellm.ai/docs/completion/token_usage
from litellm import completion_cost

# After an AI call:
response = litellm.completion(model="gpt-4o", messages=messages)
cost = response._hidden_params["response_cost"]
# Or: cost = completion_cost(completion_response=response)
usage = response.usage
prompt_tokens = usage.prompt_tokens
completion_tokens = usage.completion_tokens
```

### Pattern 3: Response Caching (FOUND-03)

**What:** Cache AI engine responses in Redis with 24h TTL to avoid redundant API calls
**When to use:** Before dispatching any AI query, check cache first

```python
# Service: cache_service.py
import hashlib
import json
from redis.asyncio import Redis as AsyncRedis

class AICacheService:
    TTL_SECONDS = 86400  # 24 hours

    def __init__(self, redis: AsyncRedis):
        self.redis = redis

    def _make_key(self, engine: str, model: str, messages: list[dict], temperature: float) -> str:
        """Deterministic cache key from query parameters."""
        payload = json.dumps({
            "engine": engine,
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }, sort_keys=True)
        return f"ai_cache:{hashlib.sha256(payload.encode()).hexdigest()}"

    async def get(self, engine: str, model: str, messages: list[dict],
                  temperature: float = 0.0) -> dict | None:
        """Check cache for existing response."""
        key = self._make_key(engine, model, messages, temperature)
        cached = await self.redis.get(key)
        if cached:
            return json.loads(cached)
        return None

    async def set(self, engine: str, model: str, messages: list[dict],
                  temperature: float, response: dict) -> None:
        """Store response in cache with TTL."""
        key = self._make_key(engine, model, messages, temperature)
        await self.redis.setex(key, self.TTL_SECONDS, json.dumps(response))
```

**Key design decisions:**
- Cache key includes `engine + model + messages + temperature` to ensure cache correctness
- `sort_keys=True` in JSON serialization ensures deterministic key generation
- 24-hour TTL (86400 seconds) matches requirement
- Use `redis.asyncio.Redis` for async compatibility with FastAPI
- Store full response JSON (text, usage, model version) for downstream processing

### Pattern 4: Outbound Rate Limiting (FOUND-04)

**What:** Throttle outbound requests to AI engines per provider to stay within their rate limits
**When to use:** Before every outbound AI API call

This is fundamentally different from the existing inbound rate limiter. The existing `rate_limiter.py` protects our API from too many incoming requests. This pattern protects us from exceeding provider API limits on outgoing requests.

```python
# In core/outbound_limiter.py
import asyncio
import time

class ProviderRateLimiter:
    """Token bucket rate limiter for outbound AI API calls."""

    def __init__(self, rpm: int, max_concurrent: int):
        """
        Args:
            rpm: Requests per minute allowed by the provider
            max_concurrent: Max concurrent requests to this provider
        """
        self.rpm = rpm
        self.interval = 60.0 / rpm  # seconds between requests
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self._last_request = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self):
        """Wait until we can make a request. Applies back-pressure."""
        await self.semaphore.acquire()
        async with self._lock:
            now = time.monotonic()
            wait_time = self._last_request + self.interval - now
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            self._last_request = time.monotonic()

    def release(self):
        """Release the semaphore after request completes."""
        self.semaphore.release()

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, *exc):
        self.release()


# Provider configurations (conservative defaults)
PROVIDER_LIMITS = {
    "openai": ProviderRateLimiter(rpm=60, max_concurrent=10),
    "anthropic": ProviderRateLimiter(rpm=60, max_concurrent=10),
    "perplexity": ProviderRateLimiter(rpm=20, max_concurrent=5),
}

# Usage:
async def call_ai_engine(engine: str, ...):
    limiter = PROVIDER_LIMITS[engine]
    async with limiter:
        response = await litellm.acompletion(...)
        return response
```

**Key design decisions:**
- `asyncio.Semaphore` controls concurrency (how many calls in-flight simultaneously)
- Token bucket interval controls RPM (pacing between requests)
- Back-pressure: callers block (await) until capacity is available -- no dropped requests
- Per-provider configuration: each AI engine gets its own limiter with different limits
- Conservative defaults: actual provider limits vary by tier and should be configurable

### Pattern 5: Alembic Setup

**What:** Database migration framework
**When to use:** Must be initialized before any model changes

```bash
cd backend
alembic init alembic
```

Then configure `alembic/env.py` to use the app's Base and DATABASE_URL:
```python
# alembic/env.py
from app.core.database import Base
from app.core.config import settings
from app.models import *  # Import all models so Base.metadata is complete

config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
target_metadata = Base.metadata
```

Remove `Base.metadata.create_all(bind=engine)` from `main.py` -- Alembic handles schema creation.

### Anti-Patterns to Avoid

- **Using `BackgroundTasks` for long-running work:** FastAPI's `BackgroundTasks` runs in the ASGI thread pool. Use Celery for anything over a few seconds. The existing analysis endpoint (M-22) must be migrated.
- **Failing open on Redis outage for cost-sensitive operations:** The existing rate limiter (M-20) silently allows all requests when Redis is down. For outbound AI rate limiting and cost tracking, fail closed (return 503) to prevent cost explosion.
- **`datetime.utcnow()` without timezone:** The existing code uses `datetime.utcnow()` which returns a naive datetime. Use `datetime.now(timezone.utc)` instead (Python 3.12+ deprecation warning).
- **Storing plaintext secrets in `.env` committed to git:** (M-23) Add `backend/.env` to `.gitignore` immediately.
- **`hmac.new()` call in `sign_request`:** (H-8) This method should use `hmac.HMAC()` or be removed if unused.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Password hashing | Custom bcrypt wrapper | `pwdlib` with `PasswordHash.recommended()` | Handles algorithm selection, timing-safe comparison, hash format detection |
| JWT creation/verification | Manual token string manipulation | `PyJWT` (`jwt.encode`/`jwt.decode`) | Handles claims validation, expiry checks, algorithm verification |
| Database migrations | `Base.metadata.create_all()` | Alembic | Supports rollback, version history, team collaboration, production deploys |
| AI cost calculation | Manual token counting + price lookup | LiteLLM `completion_cost()` | Maintains pricing database for 100+ models, handles prompt caching pricing |
| Cache key generation | String concatenation | `hashlib.sha256` of JSON-serialized params | Deterministic, handles nested structures, no key length issues |
| Rate limiting algorithm | Custom counter with sleep | `asyncio.Semaphore` + token bucket pattern | Handles concurrent access, back-pressure, no race conditions |

**Key insight:** Security and cost-control components are the worst candidates for hand-rolling. Off-the-shelf solutions handle edge cases (timing attacks, race conditions, token format changes) that take months to discover in custom code.

## Common Pitfalls

### Pitfall 1: Python-jose Breaks on Python 3.13+

**What goes wrong:** `python-jose` depends on the `crypt` module which was removed in Python 3.13. Import fails with `ModuleNotFoundError`.
**Why it happens:** Library abandoned since 2021, no maintainer to update.
**How to avoid:** Replace with `PyJWT` before any other work. This is a drop-in replacement for the JWT operations used in this codebase.
**Warning signs:** `DeprecationWarning` about crypt module on Python 3.11-3.12.

### Pitfall 2: Passlib DeprecationWarning on Python 3.11+

**What goes wrong:** `passlib` imports trigger `DeprecationWarning: 'crypt' is deprecated` on Python 3.11+. Will break entirely on Python 3.13+.
**Why it happens:** passlib uses stdlib `crypt` module which is being removed.
**How to avoid:** Replace with `pwdlib[bcrypt]`. API is similar but not identical -- `CryptContext` becomes `PasswordHash`.
**Warning signs:** Deprecation warnings in test output and server logs.

### Pitfall 3: Rate Limiter Fails Open on Redis Outage

**What goes wrong:** When Redis is unreachable, the existing rate limiter catches `RedisError` and allows all requests through (M-20).
**Why it happens:** The `except redis.RedisError: pass` pattern in `rate_limiter.py` lines 95-98 and 214-215.
**How to avoid:** For outbound AI rate limiting, fail closed. Return 503 when Redis is unavailable. For inbound rate limiting on read endpoints, failing open is acceptable.
**Warning signs:** Sudden spike in AI API costs during Redis maintenance.

### Pitfall 4: Profile Model Lacks Auth Fields

**What goes wrong:** The `Profile` model has no `email` or `password_hash` columns. It was designed to link to Supabase `auth.users` via the UUID primary key, not for self-managed auth.
**Why it happens:** Original design used Supabase for auth. The pivot to self-managed JWT auth requires Profile to store credentials directly.
**How to avoid:** Add `email` (unique, indexed) and `password_hash` columns via Alembic migration. Add `is_active` boolean for account deactivation.
**Warning signs:** Registration endpoint fails with missing column error.

### Pitfall 5: No Celery App Configuration

**What goes wrong:** The `tasks/` directory is empty. Docker-compose references `app.tasks.celery_app` but this module doesn't exist. The Celery worker container will crash on startup.
**Why it happens:** Celery infrastructure was declared but never implemented.
**How to avoid:** Create `app/tasks/__init__.py` and `app/tasks/celery_app.py` with basic Celery configuration using Redis as broker.
**Warning signs:** `ModuleNotFoundError: No module named 'app.tasks.celery_app'` in celery container logs.

### Pitfall 6: datetime.utcnow() Deprecation

**What goes wrong:** `datetime.utcnow()` returns naive datetimes (no timezone info). Python 3.12 added deprecation warnings for this.
**Why it happens:** Legacy Python pattern. The existing `security.py` uses `datetime.utcnow()` in 4 places.
**How to avoid:** Use `datetime.now(timezone.utc)` everywhere. This returns timezone-aware datetimes.
**Warning signs:** `DeprecationWarning` in Python 3.12+ output.

### Pitfall 7: Async Redis vs Sync Redis

**What goes wrong:** The existing `rate_limiter.py` uses synchronous `redis.Redis`. Mixing sync Redis calls in async FastAPI endpoints blocks the event loop.
**Why it happens:** Rate limiter was written before async Redis was standard.
**How to avoid:** Use `redis.asyncio.Redis` for all new code (cache service, outbound rate limiter). The existing sync rate limiter should be migrated but is lower priority.
**Warning signs:** Slow response times under concurrent load due to event loop blocking.

## Code Examples

### Celery App Initialization

```python
# backend/app/tasks/celery_app.py
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "geo_platform",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,  # Re-queue tasks if worker crashes
    worker_prefetch_multiplier=1,  # Fair scheduling
)
```

### Auth Schemas (Pydantic)

```python
# backend/app/schemas/auth.py
from pydantic import BaseModel, EmailStr, field_validator

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 12:
            raise ValueError("Password must be at least 12 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain an uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain a lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain a digit")
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            raise ValueError("Password must contain a special character")
        return v

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str | None
    role: str

    class Config:
        from_attributes = True
```

### Protecting Existing Endpoints

```python
# The pattern to apply to ALL audit-related endpoints:
from app.core.security import get_current_active_user

@router.post("/analyze", dependencies=[Depends(analysis_rate_limit)])
async def create_analysis(
    request: AnalyzeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(get_current_active_user),  # UNCOMMENT THIS
):
    # Use current_user.id and current_user.org_id for record ownership
    ...
```

### Updated Profile Model

```python
# backend/app/models/profile.py
from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.core.database import Base

class Profile(Base):
    __tablename__ = "profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)   # NEW
    password_hash = Column(String, nullable=False)                     # NEW
    is_active = Column(Boolean, default=True)                          # NEW
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    full_name = Column(String, nullable=True)
    role = Column(String, default="member")

    organization = relationship("Organization", back_populates="profiles")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `python-jose` for JWT | `PyJWT` | 2024 (FastAPI docs updated) | Drop-in replacement for encode/decode; import path changes |
| `passlib[bcrypt]` for passwords | `pwdlib[bcrypt]` | 2024 (FastAPI docs updated) | New API: `PasswordHash.recommended()` instead of `CryptContext` |
| `from sqlalchemy.ext.declarative import declarative_base` | `from sqlalchemy.orm import declarative_base` (or `DeclarativeBase` class) | SQLAlchemy 2.0 (2023) | Old import emits `MovedIn20Warning` |
| `datetime.utcnow()` | `datetime.now(timezone.utc)` | Python 3.12 (2023) | Old form returns naive datetime, deprecated |
| Perplexity `sonar-reasoning` | Deprecated Dec 2025 | Dec 15, 2025 | Use `sonar-pro` or `sonar` for Phase 3 |
| Perplexity `r1-1776` | Removed Aug 2025 | Aug 1, 2025 | Not available |

**Deprecated/outdated:**
- `python-jose`: Abandoned, no releases since 2021. Will break on Python 3.13.
- `passlib`: Deprecated due to `crypt` module removal. Will break on Python 3.13.
- `declarative_base()` from `sqlalchemy.ext.declarative`: Deprecated import path in SQLAlchemy 2.0.
- `Base.metadata.create_all()` in `main.py`: Replace with Alembic migrations.
- Perplexity `sonar-reasoning`: Deprecated Dec 2025.
- Perplexity `r1-1776`: Removed Aug 2025.

## Existing Codebase Concerns to Resolve in Phase 1

These items from CONCERNS.md must be addressed as part of this phase:

| Concern | Severity | Resolution in Phase 1 |
|---------|----------|-----------------------|
| H-11: Auth disabled on all endpoints | High | Uncomment `Depends(get_current_active_user)` on all protected routes after creating auth endpoints |
| M-23: `.env` committed to git | Medium | Add `backend/.env` to `.gitignore`, keep only `.env.example` |
| M-20: Rate limiter fails open | Medium | New outbound rate limiter fails closed; update inbound rate limiter for expensive endpoints |
| M-22: BackgroundTasks for long work | Medium | Initialize Celery app (needed for Phase 2+); not required to migrate existing analysis endpoint in Phase 1 |
| H-9: Random authority scores | High | Not directly Phase 1, but note: this becomes irrelevant after Phase 4 replaces scoring |
| H-4: Dual ORM Base | High | Not directly Phase 1, but `geo_data_points/` subsystem is being replaced by new audit system |
| M-13: Deprecated declarative_base import | Medium | Fix import path in `database.py` |
| L-30: ENCRYPTION_KEY regenerated on restart | Low | Raise startup error if not set in production |

## Open Questions

1. **Supabase dependency: keep or remove?**
   - What we know: `config.py` requires `SUPABASE_URL` and `SUPABASE_KEY` env vars. The Profile model's UUID PK was designed to link to Supabase auth.users. With self-managed auth, Supabase auth is redundant.
   - What's unclear: Whether other parts of the app (frontend?) use Supabase for anything beyond auth.
   - Recommendation: Keep Supabase env vars as optional (empty string default) for now. They can be removed in a cleanup phase. Focus on self-managed auth being the primary path.

2. **Per-audit budget cap: where to store the limit?**
   - What we know: The requirement says "per-audit budget cap halts execution when exceeded." A default budget per audit is needed.
   - What's unclear: Should budget be configurable per user/org/tier, or a global system default?
   - Recommendation: Start with a global default in config (`AUDIT_BUDGET_USD=1.00`), with a column on the audit record to override per-audit. Tier-based budgets can come in Phase 9 (agency features).

3. **AI provider rate limits: what are the actual limits?**
   - What we know: Limits vary by provider, tier, and account age. LiteLLM supports configuring RPM/TPM per model.
   - What's unclear: The exact limits for the project's API accounts.
   - Recommendation: Use conservative defaults (60 RPM for OpenAI/Anthropic, 20 RPM for Perplexity) and make them configurable via env vars. Actual limits should be verified against account dashboards before Phase 3.

4. **Should the schemas/ directory be created now?**
   - What we know: There is no `schemas/` directory despite `api/analysis.py` defining inline Pydantic schemas.
   - What's unclear: Whether to create a proper schemas module or keep inline schemas.
   - Recommendation: Create `app/schemas/` with separate files (`auth.py`, `analysis.py`, etc.) as part of Phase 1. This follows FastAPI best practices and keeps router files clean.

## Sources

### Primary (HIGH confidence)
- FastAPI official docs: JWT auth with PyJWT - https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
- LiteLLM official docs: Token usage and cost tracking - https://docs.litellm.ai/docs/completion/token_usage
- LiteLLM official docs: Perplexity provider support - https://docs.litellm.ai/docs/providers/perplexity
- Existing codebase: `backend/app/core/security.py`, `rate_limiter.py`, `config.py`, `database.py`
- Existing codebase: `backend/app/models/profile.py`, `organization.py`, `analysis.py`
- CONCERNS.md: 30 documented concerns with severity levels

### Secondary (MEDIUM confidence)
- FastAPI GitHub Discussion #11345: python-jose abandonment confirmed - https://github.com/fastapi/fastapi/discussions/11345
- FastAPI GitHub PR #11589: Documentation updated to PyJWT - https://github.com/fastapi/fastapi/pull/11589
- FastAPI GitHub Discussion #11773: passlib deprecation, pwdlib recommendation - https://github.com/fastapi/fastapi/discussions/11773
- pwdlib introduction: https://github.com/frankie567/pwdlib/discussions/1
- Perplexity API model deprecation (sonar-reasoning Dec 2025): https://docs.perplexity.ai/changelog/changelog
- Redis async patterns for FastAPI: https://redis.io/learn/develop/python/fastapi

### Tertiary (LOW confidence)
- AI API pricing (changes frequently): https://pricepertoken.com/pricing-page/provider/openai, https://pricepertoken.com/pricing-page/provider/perplexity
- Exact provider RPM limits (varies by account tier): Needs verification against account dashboards

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Verified against existing codebase, FastAPI official docs, and PyPI
- Architecture: HIGH - Patterns derived from existing codebase structure and FastAPI conventions
- Pitfalls: HIGH - 6 of 7 pitfalls identified from actual codebase concerns (CONCERNS.md)
- Cost tracking: MEDIUM - LiteLLM API verified via official docs, but integration untested
- Provider rate limits: LOW - Actual limits depend on account tier, conservative defaults recommended

**Research date:** 2026-02-22
**Valid until:** 2026-03-22 (30 days - stack is stable, but AI API pricing/model names may change)
