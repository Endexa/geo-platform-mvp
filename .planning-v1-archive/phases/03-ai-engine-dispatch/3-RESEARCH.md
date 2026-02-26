# Phase 3: AI Engine Dispatch - Research

**Researched:** 2026-02-22
**Domain:** Multi-provider LLM API dispatch with parallel execution, caching, and cost tracking
**Confidence:** HIGH

## Summary

Phase 3 dispatches the queries generated in Phase 2 to three AI engines (ChatGPT/OpenAI, Claude/Anthropic, Perplexity) in parallel, stores their responses with full metadata, and integrates with the existing caching and cost tracking infrastructure from Phase 1. The project already has all the foundational pieces: `AICacheService` (Redis, 24h TTL, fail-open), `ProviderRateLimiter` (per-engine semaphore + token bucket), `CostTrackingService` (per-audit budget caps), and a Celery pipeline that currently ends at query generation.

LiteLLM is already in the project (used for query generation in Phase 2) and provides the unified interface needed to call all three providers. The key implementation decision is how to run parallel calls within a Celery worker. The existing pattern uses `asyncio.run()` inside Celery tasks (see `audit_tasks.py` line 55). Since Celery workers run in a sync prefork pool, the simplest approach that aligns with the existing codebase is to use `concurrent.futures.ThreadPoolExecutor` for parallel dispatch of sync `litellm.completion()` calls -- one thread per engine per query. This avoids the event loop complexities of mixing asyncio with Celery and is consistent with how Celery handles I/O-bound work.

**Primary recommendation:** Create a `DispatchService` that takes a list of `AuditQuery` records, dispatches each to all three engines in parallel using `ThreadPoolExecutor`, integrates with the existing cache/cost/rate-limiter services, and stores results in a new `EngineResponse` model. Extend the Celery audit pipeline to add a `DISPATCHING` stage after `GENERATING_QUERIES`.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AUDIT-04 | App queries ChatGPT, Claude, and Perplexity APIs with generated queries | LiteLLM `completion()` with provider-prefixed model names (`gpt-4o`, `anthropic/claude-sonnet-4-5`, `perplexity/sonar-pro`). Existing `AuditQuery` records from Phase 2 provide the query text. ThreadPoolExecutor for parallel dispatch across engines. |
</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| litellm | >=1.17.0 (already installed) | Unified LLM API interface | Already used in Phase 2 for query generation. Provides `completion()` and `acompletion()` with automatic cost tracking via `response._hidden_params["response_cost"]`. Supports all three target providers with consistent interface. |
| concurrent.futures | stdlib | Parallel thread-based dispatch | ThreadPoolExecutor allows parallel sync `litellm.completion()` calls within a Celery task. No event loop conflicts. Each engine call runs in its own thread with I/O blocking handled natively. |

### Supporting (Already Installed)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| redis (aioredis) | 5.0.1 | AI response caching | `AICacheService` already built in Phase 1. Check cache before dispatch, store after. |
| loguru | 0.7.2 | Structured logging | Log dispatch attempts, failures, cache hits/misses per engine. |
| sqlalchemy | 2.0.25 | ORM for response storage | New `EngineResponse` model for storing AI responses with metadata. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| ThreadPoolExecutor | asyncio.run() + acompletion + asyncio.gather | Already used for crawler in Phase 2, but mixing asyncio with Celery prefork workers is fragile. ThreadPoolExecutor is simpler and more predictable for I/O-bound LLM calls. |
| ThreadPoolExecutor | celery-aio-pool | Would require changing Celery worker pool configuration globally. Too invasive for this phase. |
| litellm | Direct httpx calls per provider | Would require maintaining three separate API clients, handling auth, parsing responses, and tracking costs manually. litellm already does all of this. |

**Installation:**
```bash
# No new packages needed -- litellm, redis, sqlalchemy already installed
# Only need to add PERPLEXITYAI_API_KEY and ANTHROPIC_API_KEY to .env
```

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
├── models/
│   └── engine_response.py    # NEW: EngineResponse SQLAlchemy model
├── services/
│   ├── dispatch_service.py   # NEW: Orchestrates parallel engine dispatch
│   ├── cache_service.py      # EXISTING: Redis cache (no changes)
│   └── cost_service.py       # EXISTING: Cost tracking (no changes)
├── core/
│   └── outbound_limiter.py   # EXISTING: Rate limiters (no changes)
├── schemas/
│   └── audit.py              # EXTEND: Add engine response to audit detail
└── tasks/
    └── audit_tasks.py        # EXTEND: Add dispatch stage to pipeline
```

### Pattern 1: Engine Adapter Configuration

**What:** Define each engine's LiteLLM model name, provider key, and dispatch parameters in a single configuration dict rather than scattering them across the codebase.

**When to use:** Always. Every dispatch call needs engine name, model, and provider.

**Example:**
```python
# Source: LiteLLM docs for provider model naming
ENGINE_CONFIG = {
    "openai": {
        "model": "gpt-4o-mini",          # Cost-efficient for audit queries
        "provider": "openai",             # Rate limiter key
        "env_key": "OPENAI_API_KEY",      # Already in settings
        "temperature": 0.0,               # Reproducibility per Phase 4 requirement
    },
    "anthropic": {
        "model": "anthropic/claude-haiku-4-5",  # Cost-efficient for audit queries
        "provider": "anthropic",
        "env_key": "ANTHROPIC_API_KEY",
        "temperature": 0.0,
    },
    "perplexity": {
        "model": "perplexity/sonar",      # Standard search model (cheapest)
        "provider": "perplexity",
        "env_key": "PERPLEXITYAI_API_KEY",
        "temperature": 0.0,
    },
}
```

**Model selection rationale:**
- OpenAI: `gpt-4o-mini` -- significantly cheaper than `gpt-4o` ($0.15/$0.60 per 1M vs $2.50/$10.00), sufficient for answering brand visibility queries where we need the content of the response, not the quality of reasoning.
- Anthropic: `anthropic/claude-haiku-4-5` -- cheapest Claude model ($1/$5 per 1M tokens). We are measuring what the engine says about the brand, not asking it to reason deeply.
- Perplexity: `perplexity/sonar` -- standard search model ($1/$1 per 1M tokens + request fees). Sonar Pro would cost 3-15x more with marginal benefit for this use case.

**Cost estimate per audit (15 queries x 3 engines = 45 calls):**
- OpenAI gpt-4o-mini: ~$0.01 (short queries, ~200 token responses)
- Anthropic claude-haiku-4-5: ~$0.02
- Perplexity sonar: ~$0.02 + ~$0.23 (request fees at $5/1K)
- **Total: ~$0.26/audit** (well within the $1.00 budget cap)

### Pattern 2: Parallel Dispatch with Graceful Degradation

**What:** Use `ThreadPoolExecutor` with `concurrent.futures.as_completed()` to dispatch to all three engines simultaneously. Each engine failure is isolated -- a Perplexity timeout does not prevent OpenAI and Anthropic results from being stored.

**When to use:** For every query dispatch. All three engines should be called in parallel.

**Example:**
```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from litellm import completion

def dispatch_query_to_engines(query_text: str, audit_id: str, db: Session):
    """Dispatch a single query to all engines in parallel."""
    results = {}

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {}
        for engine_name, config in ENGINE_CONFIG.items():
            future = executor.submit(
                _call_engine,
                engine_name=engine_name,
                config=config,
                query_text=query_text,
                audit_id=audit_id,
            )
            futures[future] = engine_name

        for future in as_completed(futures):
            engine_name = futures[future]
            try:
                result = future.result(timeout=60)  # 60s per engine
                results[engine_name] = result
            except Exception as e:
                logger.error(f"Engine {engine_name} failed for query: {e}")
                results[engine_name] = None  # Graceful degradation

    return results
```

### Pattern 3: Cache-Check-Before-Dispatch

**What:** Before calling any engine, check the Redis cache. If a cached response exists for this query+engine combination, skip the API call entirely and use the cached response. This saves money and respects rate limits.

**When to use:** Every dispatch call. The cache service is already built and tested.

**Example:**
```python
import asyncio

def _call_engine(engine_name, config, query_text, audit_id):
    """Call a single engine with cache check, rate limiting, and cost tracking."""
    messages = [{"role": "user", "content": query_text}]
    cache = AICacheService()

    # 1. Check cache (need to run async cache in sync context)
    loop = asyncio.new_event_loop()
    cached = loop.run_until_complete(
        cache.get(engine_name, config["model"], messages, config["temperature"])
    )
    if cached:
        logger.info(f"Cache hit for {engine_name}")
        # Record zero-cost entry
        return {"response": cached, "cached": True}

    # 2. Acquire rate limiter (sync wrapper around async limiter)
    limiter = get_provider_limiter(config["provider"])
    loop.run_until_complete(limiter.acquire())

    try:
        # 3. Call LLM
        response = completion(
            model=config["model"],
            messages=messages,
            temperature=config["temperature"],
        )

        # 4. Extract metadata
        response_text = response.choices[0].message.content
        usage = response.usage
        cost = response._hidden_params.get("response_cost", 0.0)
        model_version = response.model  # Actual model version string

        # 5. Cache the response
        cache_data = {
            "text": response_text,
            "model": model_version,
            "usage": {"prompt_tokens": usage.prompt_tokens, "completion_tokens": usage.completion_tokens},
        }
        loop.run_until_complete(
            cache.set(engine_name, config["model"], messages, config["temperature"], cache_data)
        )

        return {
            "response_text": response_text,
            "model_version": model_version,
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "cost_usd": cost,
            "cached": False,
        }
    finally:
        limiter.release()
        loop.close()
```

### Pattern 4: Budget Check Before Each Query Batch

**What:** Before dispatching each query, check remaining budget. If the audit has exceeded its budget cap, stop dispatching and mark remaining queries as skipped.

**When to use:** Before every query dispatch round in the pipeline.

**Example:**
```python
cost_svc = CostTrackingService(db)
if not cost_svc.check_budget(audit_id):
    logger.warning(f"Audit {audit_id}: budget exceeded, skipping remaining queries")
    break
```

### Anti-Patterns to Avoid

- **Sequential engine calls:** Calling OpenAI, waiting for response, then calling Anthropic, then Perplexity. This triples the wall-clock time. Use parallel dispatch.
- **Shared event loop across threads:** Do NOT share a single asyncio event loop across ThreadPoolExecutor threads. Each thread that needs async operations should create its own loop or use sync wrappers.
- **Ignoring rate limiter on cache misses:** Even if a call fails, the rate limiter must be released. Use try/finally.
- **Storing only the response text:** Store model version, token counts, cost, and timestamp. Phase 4 needs the model version for reproducibility analysis.
- **Failing the entire audit on one engine failure:** A single engine timeout must not stop the other engines or fail the audit. Use graceful degradation.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Multi-provider LLM API interface | Custom API clients per provider | `litellm.completion()` with provider prefixes | Handles auth, response parsing, error types, cost calculation, retries. Three providers means three APIs to maintain. |
| Cost per token calculation | Token counting + price lookup tables | `response._hidden_params["response_cost"]` from litellm | LiteLLM maintains an up-to-date pricing database. Manually tracking $/token across three providers and model versions is error-prone and goes stale. |
| Response caching | New cache layer | Existing `AICacheService` | Already built, tested, fail-open, 24h TTL. Cache key includes engine+model+messages+temperature. |
| Rate limiting | New rate limiter | Existing `ProviderRateLimiter` via `get_provider_limiter()` | Already configured for openai, anthropic, perplexity with per-provider RPM and concurrency limits. |
| Budget enforcement | Custom budget check | Existing `CostTrackingService.check_budget()` | Already handles per-audit spend tracking and budget cap comparison. |

**Key insight:** Phase 1 and Phase 2 already built all the supporting infrastructure. Phase 3's job is to wire them together into a dispatch pipeline, not to rebuild any of these concerns.

## Common Pitfalls

### Pitfall 1: Event Loop Conflicts in Celery Workers
**What goes wrong:** Using `asyncio.run()` or `acompletion()` inside Celery prefork workers creates event loop conflicts. Multiple calls to `asyncio.run()` in the same process can fail or behave unpredictably.
**Why it happens:** Celery prefork workers are synchronous. asyncio.run() creates and destroys event loops. Nested or concurrent event loops cause "event loop is already running" errors.
**How to avoid:** Use sync `litellm.completion()` with `ThreadPoolExecutor` for parallelism. Each thread manages its own I/O blocking. For the async cache/rate-limiter calls, create a fresh `asyncio.new_event_loop()` per thread and close it when done.
**Warning signs:** `RuntimeError: This event loop is already running` or `RuntimeError: cannot reenter an already-running event loop`.

### Pitfall 2: Rate Limiter Not Released on Exception
**What goes wrong:** If a `litellm.completion()` call raises an exception and the rate limiter semaphore is not released, it permanently reduces concurrency for that provider.
**Why it happens:** Forgetting try/finally around the acquire/release pattern.
**How to avoid:** Always use try/finally: acquire at the top, release in finally. Or use the async context manager `async with get_provider_limiter(provider):` if in an async context.
**Warning signs:** Gradually decreasing throughput over time, eventually hanging.

### Pitfall 3: PERPLEXITYAI_API_KEY Not Set
**What goes wrong:** LiteLLM raises an `AuthenticationError` for Perplexity calls because the environment variable `PERPLEXITYAI_API_KEY` is not configured.
**Why it happens:** The project currently only has `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` in config.py. Perplexity's env var name in LiteLLM is `PERPLEXITYAI_API_KEY` (not `PERPLEXITY_API_KEY`).
**How to avoid:** Add `PERPLEXITYAI_API_KEY: str = ""` to `Settings` in `config.py`. Add it to `.env.example`. Validate at dispatch time that the key is non-empty before attempting the call.
**Warning signs:** Perplexity calls always failing with auth errors.

### Pitfall 4: Perplexity Search Request Fees Not Tracked
**What goes wrong:** Perplexity charges per-request fees ($5/1K requests) ON TOP of token costs. LiteLLM's `response_cost` may not include these search request fees.
**Why it happens:** Perplexity's pricing model is different from OpenAI/Anthropic -- it includes search context fees that are not purely token-based.
**How to avoid:** Add a fixed per-request surcharge for Perplexity calls in the cost tracking logic. Estimate $0.005 per Perplexity request as a search fee. Log a warning if LiteLLM's reported cost seems too low for Perplexity.
**Warning signs:** Budget tracking shows Perplexity as cheaper than expected. Actual Perplexity invoice higher than tracked costs.

### Pitfall 5: Audit Status Left as DISPATCHING on Failure
**What goes wrong:** If the dispatch stage crashes, the audit status stays as `DISPATCHING` forever. No subsequent pipeline stage runs, and the UI shows the audit as "in progress" indefinitely.
**Why it happens:** Missing error handling in the dispatch stage that should set status to `FAILED`.
**How to avoid:** Wrap the dispatch stage in try/except just like the existing crawl and query generation stages do. On exception, set `audit.status = AuditStatus.FAILED` with the error message.
**Warning signs:** Audits stuck in `DISPATCHING` status in the database.

### Pitfall 6: ThreadPoolExecutor Thread Count Too High
**What goes wrong:** If dispatching 15 queries x 3 engines = 45 threads simultaneously, the Celery worker may exhaust OS thread limits or memory.
**Why it happens:** Creating one thread per engine-query combination without a cap.
**How to avoid:** Use a bounded ThreadPoolExecutor (`max_workers=6` or similar) and process queries in batches. Three concurrent queries x 3 engines = 9 threads max at a time. The rate limiters will also naturally bound concurrency (max_concurrent settings).
**Warning signs:** OS errors about thread creation, Celery worker OOM kills.

## Code Examples

### EngineResponse Model
```python
# Source: Existing pattern from audit.py and audit_cost.py
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

class EngineResponse(Base):
    __tablename__ = "engine_responses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_query_id = Column(
        UUID(as_uuid=True),
        ForeignKey("audit_queries.id"),
        nullable=False,
        index=True,
    )
    engine = Column(String, nullable=False)          # "openai", "anthropic", "perplexity"
    model_version = Column(String, nullable=False)   # Actual model used (e.g., "gpt-4o-mini-2024-07-18")
    response_text = Column(Text, nullable=False)      # Full AI response
    prompt_tokens = Column(Integer, nullable=False, default=0)
    completion_tokens = Column(Integer, nullable=False, default=0)
    cost_usd = Column(Numeric(10, 6), nullable=False, default=0)
    cached = Column(Boolean, default=False)
    error_message = Column(String, nullable=True)     # Non-null if this engine failed
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
```

### Dispatch Pipeline Integration
```python
# In audit_tasks.py -- extend the existing pipeline
# After Stage 2 (generate queries), add Stage 3:

# Stage 3: Dispatch to AI engines
audit.status = AuditStatus.DISPATCHING.value
db.commit()

dispatcher = DispatchService(db)
dispatch_result = dispatcher.dispatch_all_queries(
    audit_id=audit_id,
    queries=db.query(AuditQuery).filter(AuditQuery.audit_id == audit_id).all(),
)
logger.info(
    "Audit {}: dispatched {} queries, {} responses, {} failures",
    audit_id,
    dispatch_result.total_queries,
    dispatch_result.total_responses,
    dispatch_result.total_failures,
)
```

### Environment Variable Setup
```python
# In config.py Settings class, add:
PERPLEXITYAI_API_KEY: str = ""

# Engine dispatch settings
DISPATCH_MODEL_OPENAI: str = "gpt-4o-mini"
DISPATCH_MODEL_ANTHROPIC: str = "anthropic/claude-haiku-4-5"
DISPATCH_MODEL_PERPLEXITY: str = "perplexity/sonar"
DISPATCH_TEMPERATURE: float = 0.0     # Reproducibility for Phase 4
DISPATCH_TIMEOUT_SECONDS: int = 60    # Per-engine call timeout
DISPATCH_MAX_WORKERS: int = 6         # ThreadPoolExecutor size
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Direct OpenAI SDK calls | LiteLLM unified interface | 2024+ | Single API for 100+ providers. Already adopted in this project. |
| Sequential provider calls | Parallel dispatch with ThreadPoolExecutor | Standard practice | 3x faster wall-clock time per query. |
| Manual token/cost tracking | LiteLLM auto-cost via `response._hidden_params` | litellm 1.0+ | Automatic cost calculation with up-to-date pricing. |
| Perplexity `pplx-` model names | `perplexity/sonar`, `perplexity/sonar-pro` | Late 2024 | Old `pplx-` prefixed models deprecated. New naming uses `perplexity/` prefix. |
| `claude-3-5-sonnet` | `claude-sonnet-4-5` / `claude-haiku-4-5` | Late 2025 | Anthropic renaming convention change. Use latest model names. |

**Deprecated/outdated:**
- `pplx-7b-chat`, `pplx-70b-chat`: Old Perplexity model names. Use `perplexity/sonar` or `perplexity/sonar-pro`.
- `claude-3-haiku-20240307`: Still works but newer `claude-haiku-4-5` is cheaper and better.
- Perplexity citation token billing: As of 2026, citation tokens are no longer billed for standard Sonar and Sonar Pro.

## Open Questions

1. **Perplexity search request fees in LiteLLM cost tracking**
   - What we know: Perplexity charges $5/1K requests on top of token costs. LiteLLM's `response_cost` tracks token costs.
   - What's unclear: Does LiteLLM's `response_cost` include Perplexity's per-request search fees, or only token costs?
   - Recommendation: Add a configurable Perplexity per-request surcharge (default $0.005) to cost tracking. Validate against actual Perplexity invoices after first few audits.

2. **Existing `asyncio.run()` usage in Celery**
   - What we know: The existing `audit_tasks.py` already calls `asyncio.run(crawler.crawl(url))` inside a sync Celery task.
   - What's unclear: Whether this causes issues when combined with ThreadPoolExecutor threads that also create event loops for cache/rate-limiter operations.
   - Recommendation: Refactor the cache service to expose sync wrappers (e.g., `get_sync()`, `set_sync()`) that internally create and close their own event loops, keeping async internals isolated.

3. **litellm version pinning**
   - What we know: requirements.txt pins `litellm==1.17.0` but the latest is much newer (1.72.x+).
   - What's unclear: Whether 1.17.0 supports `response._hidden_params["response_cost"]` and the latest Perplexity model names.
   - Recommendation: Test with pinned version first. If cost tracking or Perplexity models fail, upgrade litellm. The API surface for `completion()` is stable.

## Sources

### Primary (HIGH confidence)
- LiteLLM Perplexity docs: https://docs.litellm.ai/docs/providers/perplexity -- model names, env var, usage
- LiteLLM Anthropic docs: https://docs.litellm.ai/docs/providers/anthropic -- model names, env var
- LiteLLM Async docs: https://docs.litellm.ai/docs/completion/stream -- acompletion usage
- LiteLLM Token/Cost docs: https://docs.litellm.ai/docs/completion/token_usage -- response_cost, completion_cost
- Python asyncio.gather docs: https://docs.python.org/3/library/asyncio-task.html -- return_exceptions pattern
- Python concurrent.futures docs: https://docs.python.org/3/library/concurrent.futures.html -- ThreadPoolExecutor

### Secondary (MEDIUM confidence)
- Perplexity API pricing: https://docs.perplexity.ai/docs/getting-started/pricing -- token + request fees
- OpenAI pricing: https://openai.com/api/pricing/ -- gpt-4o-mini pricing
- Anthropic pricing: https://platform.claude.com/docs/en/about-claude/pricing -- claude-haiku-4-5 pricing
- LiteLLM GitHub: https://github.com/BerriAI/litellm -- async issues, Router TPM limits

### Tertiary (LOW confidence)
- Celery + asyncio patterns: https://streamhacker.com/2025/09/22/async-python-functions-with-celery/ -- celery-aio-pool recommendation
- LiteLLM async implementation details (may use executor wrapping for sync calls internally): https://github.com/BerriAI/litellm/issues/10104

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- litellm already in use, all providers documented, pricing verified with official sources
- Architecture: HIGH -- extending existing patterns (Celery pipeline, cache service, rate limiter, cost service)
- Pitfalls: HIGH -- event loop + Celery issues well-documented, rate limiter release pattern is standard, Perplexity pricing nuance verified
- Cost estimates: MEDIUM -- token costs verified with official pricing, but Perplexity search fees and LiteLLM cost tracking integration need runtime validation

**Research date:** 2026-02-22
**Valid until:** 2026-03-22 (30 days -- provider pricing may change, model names are stable)
