# Phase 3: AI Visibility Hardening - Research

**Researched:** 2026-02-26
**Domain:** Statistical AI brand visibility measurement, multi-engine LLM query dispatch, per-engine scoring with confidence indicators
**Confidence:** HIGH

## Summary

Phase 3 transforms the existing AI Visibility Score from a single-shot-per-query measurement into a statistically meaningful metric. The current system already generates 10-15 queries per audit, dispatches them to up to 4 engines (OpenAI, Anthropic, Perplexity, Gemini), detects brand mentions via exact+fuzzy matching, and computes per-engine and overall visibility scores. The core infrastructure -- dispatch, caching, rate limiting, cost tracking, mention detection -- is solid and does not need rebuilding.

The gap is narrower than it appears. The system currently sends each query once per engine (1 response per query per engine). The requirement (VIS-02) calls for statistical sampling with 5-15 queries per engine and confidence indicators. However, the system already generates 10-15 diverse queries across 5 categories, which means each engine already receives 10-15 distinct queries. The real issue is not "too few queries" but rather the lack of confidence indicators, the absence of per-query mention tracking granularity in the score display, and the need for the VisibilityScore model to surface richer statistical data (mention rate per engine, confidence level, query count per engine).

Industry research (AirOps, ALM Corp LCRS framework, Geneo) confirms that LLM brand visibility is inherently volatile -- only 30% of brands stay visible across consecutive runs. The established methodology is: run a fixed set of 10-50 queries per engine, report mention rate (percentage of queries with at least one mention) per engine, and track trends over time rather than trusting single-point measurements. The existing system already follows this pattern structurally; it needs hardening, not replacement.

**Primary recommendation:** Enhance the VisibilityScore model and ScoringService to surface per-engine statistical data (queries_sent, mentions_found, mention_rate, confidence_level) and expose this in the API and frontend. Add the ability to rerun queries for same-audit consistency checks. Ensure cache TTL alignment produces stable results within the TTL window.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| VIS-01 | AI Visibility Score derived from real LLM queries across active engines (not fabricated) | Already implemented: dispatch_service.py sends queries to engines with valid API keys via LiteLLM; scoring_service.py computes scores from real BrandMention records. The score is real, not fabricated. Hardening means adding transparency (showing how many queries produced the score). |
| VIS-02 | Statistical sampling: multiple queries per engine for meaningful measurement with confidence indicators | The system generates 10-15 queries and sends all to each active engine. This IS multiple queries per engine. The gap is: no confidence indicators shown to the user. Need to add confidence_level field to VisibilityScore, compute it from sample size and mention rate variance, and expose in API/frontend. |
| VIS-03 | Per-engine breakdown showing visibility on ChatGPT, Claude, Perplexity, Gemini separately | Already implemented: VisibilityScore.per_engine_scores stores {"openai": 75, "anthropic": 60}. Frontend AuditResults.vue renders per-engine cards. Gap: display engine-friendly names (ChatGPT not "openai"), show mention_rate and query count per engine, not just a score. |
| VIS-04 | Graceful degradation: engines without API keys are skipped, score adjusts to available engines | Already implemented: DispatchService.__init__ pre-computes _active_engines by checking API keys. ScoringService averages only engines that have responses. Gap: the frontend should explicitly show which engines were queried vs skipped, and the algorithm should not penalize audits with fewer engines. |
</phase_requirements>

## Standard Stack

### Core (already in project)

| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| LiteLLM | pinned (legacy) | Unified LLM API for all 4 engines | Working, used in dispatch_service.py |
| RapidFuzz | current | Fuzzy brand mention detection | Working, used in mention_detector.py |
| SQLAlchemy | current | ORM for VisibilityScore, EngineResponse, BrandMention | Working |
| redis.asyncio | current | Cache layer for AI responses (24h TTL) | Working, cache_service.py |
| Pydantic v2 | current | Request/response schemas, structured LLM output | Working |

### Supporting (already in project)

| Library | Version | Purpose | When Used |
|---------|---------|---------|-----------|
| Loguru | current | Structured logging throughout pipeline | Every service |
| concurrent.futures | stdlib | ThreadPoolExecutor for parallel engine dispatch | dispatch_service.py |

### No New Dependencies Needed

This phase requires zero new libraries. All infrastructure exists. The work is enhancing models, scoring logic, and API responses.

### Alternatives Considered

| Instead of | Could Use | Why Not |
|------------|-----------|---------|
| Running duplicate queries per engine | Use existing 10-15 diverse queries per engine | Duplicate queries waste budget and provide marginally more data; diverse queries across categories give a richer signal |
| Statistical confidence intervals (scipy) | Simple mention rate + sample size thresholds | Scipy adds a dependency for minimal benefit; mention rate with query count is sufficient for user-facing confidence |
| Weighted engine averaging | Equal-weight engine averaging (current) | Engine weighting (e.g., Google 0.5, Perplexity 0.3) is opinionated and hard to justify; equal weights are transparent |

## Architecture Patterns

### Current Data Flow (mostly unchanged)

```
audit_tasks.py Stage 2: QueryGeneratorService.generate()
  -> 10-15 queries stored in audit_queries table

audit_tasks.py Stage 3: DispatchService.dispatch_all_queries()
  -> Each query sent to all active engines (up to 4)
  -> 40-60 engine_responses total (10-15 queries x 4 engines)

audit_tasks.py Stage 4: MentionDetectorService + ScoringService
  -> Brand mentions detected per response
  -> VisibilityScore computed and stored
```

### Pattern 1: Enhanced VisibilityScore Model

**What:** Add richer per-engine statistical data to the VisibilityScore model.
**Current state:** `per_engine_scores` is a JSONB field storing `{"openai": 75, "anthropic": 60}` -- just a score per engine.
**Target state:** `per_engine_breakdown` stores richer data per engine:

```python
# Target per_engine_scores JSONB structure:
{
    "openai": {
        "score": 75,
        "queries_sent": 12,
        "queries_with_mentions": 9,
        "mention_rate": 75.0,
        "total_mentions": 14,
        "avg_confidence": 92,
        "skipped": False,
    },
    "anthropic": {
        "score": 60,
        "queries_sent": 12,
        "queries_with_mentions": 7,
        "mention_rate": 58.3,
        "total_mentions": 9,
        "avg_confidence": 85,
        "skipped": False,
    },
    "perplexity": {
        "score": 0,
        "queries_sent": 0,
        "queries_with_mentions": 0,
        "mention_rate": 0,
        "total_mentions": 0,
        "avg_confidence": 0,
        "skipped": True,
        "skip_reason": "No API key configured"
    },
    "gemini": {
        "score": 45,
        "queries_sent": 12,
        "queries_with_mentions": 5,
        "mention_rate": 41.7,
        "total_mentions": 6,
        "avg_confidence": 78,
        "skipped": False,
    }
}
```

**Migration approach:** The `per_engine_scores` column is already JSONB. No schema migration needed -- just store richer data in the same column. Old audits with the simple `{"openai": 75}` format will be handled by the frontend with fallback rendering.

### Pattern 2: Confidence Level Calculation

**What:** Derive a confidence level from query count and mention rate consistency.
**When to use:** After computing per-engine scores.

```python
def compute_confidence_level(queries_sent: int, mention_rate: float) -> str:
    """Derive confidence level from sample size and mention rate.

    Thresholds based on industry practice (AirOps, ALM Corp LCRS):
    - HIGH: 10+ queries per engine, any mention rate
    - MEDIUM: 5-9 queries per engine
    - LOW: 1-4 queries per engine

    Special case: 0 queries = NOT_MEASURED (engine was skipped)
    """
    if queries_sent == 0:
        return "not_measured"
    elif queries_sent >= 10:
        return "high"
    elif queries_sent >= 5:
        return "medium"
    else:
        return "low"
```

### Pattern 3: Cache Consistency for Reproducibility (VIS-04)

**What:** Ensure that re-running the same audit within the cache TTL produces the same visibility score.
**Current state:** The cache uses `temperature=0.0` (configured in `DISPATCH_TEMPERATURE`) and SHA-256 key hashing. Same query + same engine + same temperature = cache hit.
**Gap:** The cache TTL is 24 hours (`AI_CACHE_TTL_SECONDS = 86400`). The requirement says "within the cache TTL." This is already satisfied by the existing cache implementation. The only risk is if queries are regenerated differently on the second run (because query generation uses `temperature=0.7`).

**Solution:** The audit pipeline does NOT regenerate queries on re-run. A new audit for the same URL generates new queries (via the LLM), but the AI engine responses for those specific query texts will be cached. If the user runs audit #2 for the same URL and the QueryGeneratorService generates the same queries (likely at temp=0.7), the dispatch responses will come from cache. If different queries are generated, different responses are expected.

For strict reproducibility within TTL, the system should document that the "consistency" guarantee applies to the engine dispatch layer (same query text -> same response from cache), not the query generation layer. The VIS-04 success criterion "Running the same audit twice within the cache TTL produces consistent results" should be interpreted as: same queries dispatched within the TTL will produce the same engine responses, and therefore the same mention analysis and visibility score.

### Pattern 4: Engine Display Name Mapping

**What:** Map internal engine keys to user-friendly display names.

```python
ENGINE_DISPLAY_NAMES = {
    "openai": "ChatGPT",
    "anthropic": "Claude",
    "perplexity": "Perplexity",
    "gemini": "Gemini",
}
```

This mapping should be applied in the API response (not just the frontend) so that the per-engine breakdown uses recognizable names.

### Anti-Patterns to Avoid

- **Do not send duplicate queries to achieve "more samples."** The 10-15 diverse queries already provide statistical sampling. Sending each query 3 times would triple costs (~$0.30->$0.90 per audit) with minimal measurement improvement, and cached responses would return identical results anyway.

- **Do not average per-engine scores into the overall score without weighting by query count.** An engine that answered 12 queries should have more influence than one that answered 3 (due to rate limit hits). Use weighted average by queries_sent.

- **Do not compute confidence intervals with scipy.** This adds complexity and a dependency for negligible user value. "HIGH/MEDIUM/LOW confidence based on 12 queries" is more useful to users than "30% +/- 8.5% (95% CI)."

- **Do not change the cache TTL to longer than 24h for this phase.** The PITFALLS.md recommends 7-day TTL for AI responses, but this is a separate optimization that affects costs and freshness. Changing TTL is a config-level decision, not a Phase 3 code change.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LLM API calls | Custom HTTP client per engine | LiteLLM (already used) | Handles 4+ provider APIs with one interface |
| Fuzzy brand matching | String similarity from scratch | RapidFuzz MentionDetectorService (already used) | Proven deduplication, variant generation, context extraction |
| Cache key generation | Manual string concatenation | AICacheService SHA-256 hashing (already used) | Deterministic, collision-resistant |
| Rate limiting | Sleep-based delays | ProviderRateLimiter (already used) | Semaphore + token bucket, per-provider |

**Key insight:** Phase 3 is an enhancement phase, not a new-build phase. Every infrastructure component exists and works. The work is about making the existing visibility measurement transparent and trustworthy, not replacing the measurement system.

## Common Pitfalls

### Pitfall 1: Over-Engineering the Statistical Model

**What goes wrong:** Building a full statistical confidence interval system (binomial proportions, Wilson score intervals, bootstrap sampling) for a metric that users interpret as "high/medium/low."
**Why it happens:** Developer instinct to be mathematically rigorous. But users don't understand "30% +/- 8.5% at 95% confidence" -- they understand "Mentioned in 9 of 12 queries (HIGH confidence)."
**How to avoid:** Use simple thresholds (HIGH/MEDIUM/LOW) based on sample size. Display the raw numbers (queries_sent, queries_with_mentions) so users can judge for themselves.
**Warning signs:** Adding scipy as a dependency, computing p-values, displaying confidence intervals.

### Pitfall 2: Breaking the Existing Scoring Contract

**What goes wrong:** Changing the VisibilityScore computation formula or the per_engine_scores JSONB structure in a way that breaks the frontend or API consumers of existing audits.
**Why it happens:** The per_engine_scores column currently stores `{"openai": 75}`. If the code now stores `{"openai": {"score": 75, ...}}`, any code reading the old format will break.
**How to avoid:** Make the enhanced structure backward-compatible. The ScoringService should detect old format (integer value) vs new format (dict with "score" key) and handle both. The API schema should use Optional fields for new data. The frontend should render gracefully when new fields are missing.
**Warning signs:** Frontend crashes on old audit detail pages. API 500 errors on audits created before Phase 3.

### Pitfall 3: Ignoring the Query Generation Temperature

**What goes wrong:** The VIS-04 reproducibility requirement fails because QueryGeneratorService uses `temperature=0.7`, meaning different audits for the same URL may generate different queries.
**Why it happens:** The LLM generates queries creatively (intentionally) so that different audits explore different aspects of the brand. This is actually desirable for measurement diversity, but it means two audits for the same URL within the cache TTL might still produce different visibility scores.
**How to avoid:** Document clearly: reproducibility applies to the dispatch+scoring layer (same queries -> same responses -> same score), not the query generation layer. If strict reproducibility is needed, implement a "re-score" endpoint that reuses existing audit queries with fresh engine responses.
**Warning signs:** QA runs the same URL twice and gets different scores, files a bug.

### Pitfall 4: Not Surfacing Skipped Engines to Users

**What goes wrong:** An audit runs with only 2 engines (no Anthropic or Perplexity API keys), but the UI shows "Visibility Score: 45" without indicating that only 2 of 4 engines were queried. The user thinks their brand is invisible on Claude and Perplexity when in reality those engines were never checked.
**Why it happens:** The backend already handles skipping gracefully (DispatchService pre-filters _active_engines), but the API response and frontend don't differentiate between "engine returned 0 mentions" and "engine was never queried."
**How to avoid:** Include skipped engines in the per_engine_breakdown with `"skipped": true` and `"skip_reason"`. The frontend should render skipped engines with a distinct visual treatment (e.g., "Not configured" badge instead of a score).
**Warning signs:** Users confused about why some engines show score 0 vs not appearing at all.

### Pitfall 5: Cost Escalation from Query Multiplication

**What goes wrong:** Interpreting VIS-02 ("5-15 queries each") as "run 15 additional queries per engine beyond the existing 10-15" -- effectively tripling the query count and costs.
**Why it happens:** Ambiguous reading of the requirement. "5-15 queries each" could mean 5-15 queries per engine (already satisfied) or 5-15 additional measurement queries per engine.
**How to avoid:** The current 10-15 queries dispatched to each engine already satisfies "5-15 queries each." The success criterion says "mention rates and confidence indicators shown to the user" -- this is about transparency, not more queries.
**Warning signs:** Budget per audit jumping from ~$0.10-0.15 to $0.30-0.45.

## Code Examples

### Example 1: Enhanced ScoringService.compute_audit_score()

```python
# Source: existing backend/app/services/scoring_service.py (enhanced)

def compute_audit_score(self, audit_id: str, total_queries: int) -> VisibilityScore:
    """Compute visibility score with per-engine statistical breakdown."""

    # ... (existing mention and response loading logic) ...

    # Compute per-engine breakdown (enhanced)
    per_engine_breakdown: dict[str, dict] = {}

    for engine, engine_responses in responses_by_engine.items():
        engine_mentions = mentions_by_engine.get(engine, [])
        mentions_by_response = defaultdict(list)
        for m in engine_mentions:
            mentions_by_response[str(m.engine_response_id)].append(m)

        queries_sent = len(engine_responses)
        queries_with_mentions = len(mentions_by_response)
        mention_rate = (queries_with_mentions / queries_sent * 100) if queries_sent > 0 else 0
        total_mentions_for_engine = len(engine_mentions)
        avg_confidence = (
            sum(m.confidence for m in engine_mentions) / len(engine_mentions)
            if engine_mentions else 0
        )

        score = self._compute_per_engine_score(
            mentions_by_response=mentions_by_response,
            total_responses_for_engine=queries_sent,
        )

        per_engine_breakdown[engine] = {
            "score": score,
            "queries_sent": queries_sent,
            "queries_with_mentions": queries_with_mentions,
            "mention_rate": round(mention_rate, 1),
            "total_mentions": total_mentions_for_engine,
            "avg_confidence": round(avg_confidence),
            "confidence_level": self._compute_confidence_level(queries_sent),
            "skipped": False,
        }

    # Add skipped engines
    from app.services.dispatch_service import ENGINE_CONFIG
    for engine_name in ENGINE_CONFIG:
        if engine_name not in per_engine_breakdown:
            api_key = getattr(settings, ENGINE_CONFIG[engine_name]["api_key_setting"], "")
            per_engine_breakdown[engine_name] = {
                "score": 0,
                "queries_sent": 0,
                "queries_with_mentions": 0,
                "mention_rate": 0,
                "total_mentions": 0,
                "avg_confidence": 0,
                "confidence_level": "not_measured",
                "skipped": True,
                "skip_reason": "No API key configured" if not api_key else "No responses received",
            }

    # Overall score: weighted average by queries_sent (not equal weight)
    total_weighted_score = 0
    total_weight = 0
    for engine_data in per_engine_breakdown.values():
        if not engine_data["skipped"] and engine_data["queries_sent"] > 0:
            total_weighted_score += engine_data["score"] * engine_data["queries_sent"]
            total_weight += engine_data["queries_sent"]

    overall_score = round(total_weighted_score / total_weight) if total_weight > 0 else 0

    # Overall confidence level
    active_engines = [e for e in per_engine_breakdown.values() if not e["skipped"]]
    total_queries_sent = sum(e["queries_sent"] for e in active_engines)
    overall_confidence = self._compute_confidence_level(total_queries_sent // max(len(active_engines), 1))

    return VisibilityScore(
        id=uuid.uuid4(),
        audit_id=audit_id,
        overall_score=overall_score,
        per_engine_scores=per_engine_breakdown,  # enhanced JSONB
        mention_count=len(mentions),
        query_mention_rate=query_mention_rate,
        algorithm_version="v2",  # bump version
        # New fields (via model enhancement):
        # confidence_level=overall_confidence,
        # engines_queried=len(active_engines),
        # engines_skipped=len(per_engine_breakdown) - len(active_engines),
    )

@staticmethod
def _compute_confidence_level(queries_per_engine: int) -> str:
    if queries_per_engine == 0:
        return "not_measured"
    elif queries_per_engine >= 10:
        return "high"
    elif queries_per_engine >= 5:
        return "medium"
    else:
        return "low"
```

### Example 2: Enhanced VisibilityScore Model

```python
# Source: backend/app/models/visibility_score.py (enhanced)

class VisibilityScore(Base):
    __tablename__ = "visibility_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id = Column(UUID(as_uuid=True), ForeignKey("audits.id"), unique=True, nullable=False, index=True)
    overall_score = Column(Integer, nullable=False)  # 0-100
    per_engine_scores = Column(JSONB, nullable=False)  # Enhanced: full breakdown per engine
    mention_count = Column(Integer, nullable=False, default=0)
    query_mention_rate = Column(Numeric(5, 2), nullable=False)
    algorithm_version = Column(String, nullable=False, default="v2")
    # New columns:
    confidence_level = Column(String, nullable=False, default="low")  # high/medium/low/not_measured
    engines_queried = Column(Integer, nullable=False, default=0)
    engines_skipped = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    audit = relationship("Audit", backref="visibility_score")
```

### Example 3: Enhanced API Schema

```python
# Source: backend/app/schemas/audit.py (enhanced)

class PerEngineBreakdown(BaseModel):
    """Statistical breakdown for a single engine."""
    score: int
    queries_sent: int
    queries_with_mentions: int
    mention_rate: float
    total_mentions: int
    avg_confidence: int
    confidence_level: str  # high/medium/low/not_measured
    skipped: bool
    skip_reason: Optional[str] = None
    display_name: str  # "ChatGPT", "Claude", "Perplexity", "Gemini"

class VisibilityScoreSchema(BaseModel):
    """Enhanced schema with confidence indicators and per-engine breakdown."""
    model_config = ConfigDict(from_attributes=True)

    overall_score: int
    per_engine_scores: dict  # backward-compatible (old format: {"openai": 75}, new: {"openai": {...}})
    per_engine_breakdown: list[PerEngineBreakdown] = []  # new: structured list for frontend
    mention_count: int
    query_mention_rate: float
    algorithm_version: str
    confidence_level: str = "low"
    engines_queried: int = 0
    engines_skipped: int = 0
```

### Example 4: Frontend Per-Engine Card (Enhanced)

```vue
<!-- Source: frontend/components/AuditResults.vue (enhanced per-engine section) -->
<div v-for="engine in perEngineBreakdown" :key="engine.key"
     class="bg-white rounded-lg border border-gray-200 p-6">
  <div class="flex items-center justify-between mb-2">
    <p class="text-sm font-medium text-gray-500">{{ engine.displayName }}</p>
    <span v-if="engine.skipped"
          class="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-500">
      Not configured
    </span>
    <span v-else
          class="text-xs px-2 py-0.5 rounded-full"
          :class="confidenceBadgeClass(engine.confidence_level)">
      {{ engine.confidence_level }} confidence
    </span>
  </div>

  <p v-if="!engine.skipped" class="text-3xl font-bold font-mono"
     :class="getScoreColor(engine.score)">
    {{ engine.score }}
  </p>
  <p v-else class="text-2xl text-gray-300 font-mono">--</p>

  <div v-if="!engine.skipped" class="mt-2 text-xs text-gray-500 space-y-0.5">
    <p>Mentioned in {{ engine.queries_with_mentions }} of {{ engine.queries_sent }} queries</p>
    <p>{{ engine.mention_rate }}% mention rate</p>
  </div>
</div>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single-query brand check | Multi-query statistical sampling (10-50 queries) | 2025, driven by AirOps research showing 30% consistency | Industry standard shifted from binary "mentioned/not" to mention rate |
| Single-engine visibility | Per-engine breakdown (ChatGPT, Claude, Perplexity, Gemini) | 2025-2026, LCRS framework | Each engine has different citation behavior; averaging is misleading |
| Opaque score (just a number) | Transparent breakdown (queries sent, mention rate, confidence) | 2025-2026, Geneo, AccuRanker | Users demand knowing how the score was derived |
| Temperature-based reproducibility | Cache-based reproducibility + trend tracking | 2025, as temperature=0 proven non-deterministic | Cache is more reliable than temperature for reproducibility |

**Deprecated/outdated:**
- Single-shot visibility checks: Industry consensus is that a single query per engine is meaningless for brand visibility measurement (AirOps: 30% consistency across runs)
- Binary mention detection: Should be mention_rate (percentage) not mentioned/not_mentioned
- Engine-averaged single score: Per-engine breakdown is now table stakes for GEO tools

## Open Questions

1. **Should the overall score use weighted-by-queries-sent or equal-weight averaging?**
   - What we know: Current system uses equal weight (mean of per-engine scores). Industry tools vary -- Geneo weights by platform importance (Google 0.5, Perplexity 0.3, ChatGPT 0.2).
   - What's unclear: Whether users prefer equal treatment of engines or weighting by "market importance."
   - Recommendation: Switch to weighted-by-queries-sent (engines that answered more queries have more statistical weight). This is mathematically defensible and handles partial failures gracefully. Defer engine-importance weighting to v3 when user feedback is available.

2. **Should we add a "re-score" endpoint that reruns visibility analysis on existing queries?**
   - What we know: VIS-04 requires consistency within cache TTL. A full re-audit generates new queries (temperature=0.7), potentially changing the score.
   - What's unclear: Whether users expect to "re-run" just the visibility portion without a full re-audit.
   - Recommendation: Out of scope for Phase 3. The current behavior (new audit = new queries = potentially different score) is correct and well-understood. Document this behavior.

3. **Algorithm version migration: should old audits be retroactively rescored?**
   - What we know: Changing algorithm_version from "v1" to "v2" means old audits have v1 scores and new audits have v2 scores. The per_engine_scores JSONB format changes.
   - What's unclear: Whether the frontend should handle both formats or whether a migration script should update old data.
   - Recommendation: Handle both formats in the API layer. Old audits with `{"openai": 75}` format should be served as-is with missing fields defaulting to null/0. No retroactive rescoring -- old data is historical.

## Sources

### Primary (HIGH confidence)
- Existing codebase: `backend/app/services/dispatch_service.py`, `scoring_service.py`, `mention_detector.py`, `query_generator.py`, `cache_service.py` -- direct code reading
- Existing models: `visibility_score.py`, `engine_response.py`, `audit_query.py`, `brand_mention.py` -- direct code reading
- Existing config: `core/config.py` -- DISPATCH_TEMPERATURE=0.0, AI_CACHE_TTL_SECONDS=86400
- Alembic migration 005: visibility_scores and brand_mentions table schemas
- `.planning/research/PITFALLS.md` Pitfall 2: AI Visibility Score Non-Determinism -- project-internal research

### Secondary (MEDIUM confidence)
- [AirOps: AI Visibility Metrics That Matter](https://www.airops.com/blog/ai-visibility-metrics) -- 5-metric framework: Citation Share, Competitive SOV, Mention Rate, Sentiment, Drift/Volatility; 30% brand consistency across runs; 20-50 query packs recommended
- [AirOps: LLM Brand Citation Tracking](https://www.airops.com/blog/llm-brand-citation-tracking) -- 800 queries analyzed, 45,000+ citations; "mentioned and cited" 40% more stable than "cited-only"
- [ALM Corp: LCRS Framework](https://almcorp.com/blog/llm-consistency-recommendation-share-measurement-framework/) -- LLM Consistency + Recommendation Share; measures across prompt variation, platforms, and time
- [Geneo: AI Search Visibility Score Calculation](https://geneo.app/blog/ai-search-visibility-score-calculation/) -- Formula: Contribution(p,E) = Presence x Prominence x ExpectedClicks; per-engine then cross-engine weighted aggregation
- [AccuRanker: 5 LLM Visibility Metrics 2026](https://www.accuranker.com/blog/llm-visibility-metrics-2026/) -- Industry metrics overview
- [SugiV Blog: Temperature=0 Non-Determinism](https://blog.sugiv.fyi/temperature-determinism-llm-inference) -- temperature=0 does not guarantee deterministic output; cache is more reliable
- [LiteLLM Caching Docs](https://docs.litellm.ai/docs/proxy/caching) -- LiteLLM's caching system stores and reuses LLM responses; seed parameter "best effort" not guaranteed

### Tertiary (LOW confidence)
- [Search Engine Land: LLM Optimization 2026](https://searchengineland.com/llm-optimization-tracking-visibility-ai-discovery-463860) -- General trends article
- [Brainlabs: Rethinking Marketing Metrics for AI Visibility](https://www.brainlabsdigital.com/ai-visibility-measurement-metrics/) -- Framework overview without methodology detail

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already in the project and working
- Architecture: HIGH -- enhancement of existing proven architecture, not new build
- Pitfalls: HIGH -- grounded in codebase analysis and cross-referenced with industry research
- Requirements mapping: HIGH -- every VIS requirement mapped to existing code with specific gaps identified

**Research date:** 2026-02-26
**Valid until:** 2026-03-26 (30 days -- stable domain, no fast-moving dependencies)
