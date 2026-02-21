# Architecture Patterns

**Domain:** AI Brand Visibility Auditing Platform
**Researched:** 2026-02-21
**Confidence:** HIGH (based on existing codebase analysis + established async orchestration patterns)

---

## Recommended Architecture

The AI brand visibility auditing system adds three major subsystems to the existing FastAPI + Nuxt 3 + PostgreSQL stack. These subsystems integrate into the existing 4-layer backend (middleware, routers, services, models) without disrupting what works.

### High-Level System View

```
                        ┌─────────────────────────────────────────────┐
                        │  Nuxt 3 SPA Frontend                        │
                        │  Audit Dashboard + Results + Gap Analysis    │
                        └──────────────────┬──────────────────────────┘
                                           │ HTTP/JSON
                                           ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  FastAPI Application                                                         │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  API Routers                                                         │   │
│  │  POST /audit/start     GET /audit/{id}     GET /audit/{id}/results   │   │
│  └──────────────────────────┬───────────────────────────────────────────┘   │
│                              │                                               │
│  ┌───────────────────────────┴───────────────────────────────────────────┐  │
│  │                        Service Layer                                   │  │
│  │                                                                        │  │
│  │  ┌─────────────────┐  ┌──────────────────┐  ┌─────────────────────┐  │  │
│  │  │ AuditOrchestrator│  │ QueryGenerator   │  │ ScoringPipeline     │  │  │
│  │  │ (coordinates     │  │ (crawl site,     │  │ (site signals +     │  │  │
│  │  │  full audit flow)│  │  extract context, │  │  AI presence =      │  │  │
│  │  │                  │  │  generate queries)│  │  final score)       │  │  │
│  │  └────────┬─────────┘  └─────────┬────────┘  └──────────┬──────────┘  │  │
│  │           │                      │                       │             │  │
│  │  ┌────────┴──────────────────────┴───────────────────────┴──────────┐  │  │
│  │  │                   AIEngineOrchestrator                            │  │  │
│  │  │  (parallel dispatch to ChatGPT, Claude, Perplexity               │  │  │
│  │  │   with per-engine rate limits + retries)                         │  │  │
│  │  └──────┬──────────────────┬──────────────────┬─────────────────────┘  │  │
│  │         │                  │                   │                        │  │
│  │  ┌──────┴─────┐   ┌───────┴──────┐   ┌───────┴───────┐               │  │
│  │  │ OpenAI     │   │ Anthropic    │   │ Perplexity    │               │  │
│  │  │ Adapter    │   │ Adapter      │   │ Adapter       │               │  │
│  │  └────────────┘   └──────────────┘   └───────────────┘               │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────┘
         │                    │                     │
         ▼                    ▼                     ▼
   ┌──────────┐        ┌──────────┐          ┌──────────┐
   │PostgreSQL│        │  Redis   │          │ Celery   │
   │+ pgvector│        │  Cache   │          │ Worker   │
   └──────────┘        └──────────┘          └──────────┘
```

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| **AuditOrchestrator** | Coordinates end-to-end audit flow: site crawl, query generation, AI dispatch, scoring, result assembly | QueryGenerator, AIEngineOrchestrator, ScoringPipeline, DB |
| **QueryGenerator** | Crawls target URL, extracts industry/brand/product signals, generates industry-relevant questions for AI engines | Site crawling utils (BeautifulSoup/Playwright), LLM for question generation |
| **AIEngineOrchestrator** | Dispatches queries to multiple AI APIs in parallel with rate limiting, retries, and response normalization | Engine adapters (OpenAI, Anthropic, Perplexity), Redis (rate limit state) |
| **Engine Adapters** | Thin wrappers around each AI API. Normalize request/response format. Handle auth, retries, error mapping | External AI APIs |
| **ScoringPipeline** | Combines site-readiness signals (structured data, content quality) with AI presence analysis (mentions, sentiment, accuracy) into a 0-100 score | DB for site analysis data, AI response data |
| **ResponseAnalyzer** | Parses AI responses to detect brand mentions, extract quotes, identify competitors, assess sentiment | pgvector for semantic comparison |
| **CacheLayer** | Deduplicates AI queries, caches responses by query hash + engine + date window | Redis |

---

## Data Flow

### Complete Audit Flow (Main Pipeline)

```
User submits URL on frontend
        │
        │ POST /api/v1/audit/start  { url, brand_name?, competitors? }
        ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. AuditOrchestrator.start_audit()                             │
│     - Create Audit record (status=pending)                      │
│     - Dispatch Celery task                                      │
│     - Return audit_id immediately                               │
└───────────────────────────┬─────────────────────────────────────┘
                            │  (Celery worker picks up)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. PHASE 1: Site Crawl + Context Extraction                    │
│     QueryGenerator.analyze_site(url)                            │
│     - Crawl URL with BeautifulSoup (+ Playwright for JS sites) │
│     - Extract: brand name, industry, products/services,         │
│       competitors mentioned, structured data, meta description  │
│     - Store SiteCrawlResult in DB                               │
│     - Update audit status → "site_analyzed"                     │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. PHASE 2: Query Generation                                   │
│     QueryGenerator.generate_queries(site_context)               │
│     - Use LLM to generate 5-10 industry-relevant questions      │
│       e.g., "What are the best CRM tools for small business?"   │
│     - Include brand-specific queries:                           │
│       "What do you know about [brand_name]?"                    │
│     - Include competitor-comparison queries:                    │
│       "Compare [brand] vs [competitor]"                         │
│     - Store generated queries in DB                             │
│     - Update audit status → "queries_generated"                 │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. PHASE 3: AI Engine Querying (the expensive part)            │
│     AIEngineOrchestrator.execute_queries(queries, engines)       │
│                                                                  │
│     For each query x engine combination:                        │
│       a. Check Redis cache (query_hash + engine + date_window)  │
│       b. If cached → use cached response                        │
│       c. If not → dispatch through engine adapter               │
│          - asyncio.Semaphore per engine for rate limiting        │
│          - Exponential backoff on 429/5xx                        │
│          - Store response + metadata in DB                      │
│       d. All engines queried in parallel (within rate limits)    │
│                                                                  │
│     Result: List of AIEngineResponse records in DB              │
│     Update audit status → "ai_queried"                          │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  5. PHASE 4: Response Analysis                                   │
│     ResponseAnalyzer.analyze_responses(responses, brand_info)    │
│                                                                  │
│     For each AI response:                                        │
│       a. Detect brand mentions (exact + fuzzy match)            │
│       b. Extract quotes containing brand                        │
│       c. Identify competitor mentions                           │
│       d. Assess sentiment (positive/neutral/negative)           │
│       e. Check factual accuracy against site content            │
│       f. Store BrandMention records                             │
│                                                                  │
│     pgvector: Compare AI's description of brand vs site's       │
│     own description → alignment score                           │
│     Update audit status → "responses_analyzed"                  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  6. PHASE 5: Scoring + Report Generation                         │
│     ScoringPipeline.compute_scores(site_data, ai_analysis)      │
│                                                                  │
│     Site Readiness Score (0-100):                                │
│       - Structured data presence (schema.org, JSON-LD)          │
│       - Content quality signals (readability, depth)            │
│       - Authority signals (E-E-A-T markers)                     │
│       - AI crawler accessibility (robots.txt, sitemap)          │
│                                                                  │
│     AI Presence Score (0-100):                                   │
│       - Mention frequency across engines                        │
│       - Quote accuracy (does AI describe brand correctly?)      │
│       - Sentiment score                                         │
│       - Competitive positioning (rank vs competitors)           │
│                                                                  │
│     Final GEO Score = (site_readiness * 0.3) +                  │
│                       (ai_presence * 0.7)                       │
│                                                                  │
│     Generate gap analysis:                                       │
│       - "Competitor X mentioned for [topic] but you are not"    │
│       - "AI describes your brand as [X] but your site says [Y]" │
│                                                                  │
│     Update audit status → "completed"                           │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
Frontend polls GET /api/v1/audit/{id} → receives completed results
```

### Data Flow for Cost Efficiency (Cache Layer)

```
Query arrives at AIEngineOrchestrator
        │
        ▼
┌───────────────────────────────────────────────┐
│  Cache Check (Redis)                           │
│  Key: sha256(query_text + engine_id)           │
│  TTL: 24 hours (configurable per engine)       │
│                                                │
│  HIT  → Return cached AIEngineResponse         │
│  MISS → Proceed to API call                    │
└───────────────────────────┬────────────────────┘
                            │ MISS
                            ▼
┌───────────────────────────────────────────────┐
│  Deduplication Check                           │
│  "Is another audit currently querying the     │
│   same query+engine?"                          │
│  Redis lock: query_hash:engine:in_flight       │
│                                                │
│  YES → Wait for existing result (pub/sub)      │
│  NO  → Acquire lock, proceed                   │
└───────────────────────────┬────────────────────┘
                            │ NO (first requester)
                            ▼
┌───────────────────────────────────────────────┐
│  Rate Limit Gate (asyncio.Semaphore)           │
│  Per-engine concurrency:                       │
│    ChatGPT:    max 3 concurrent                │
│    Claude:     max 3 concurrent                │
│    Perplexity: max 5 concurrent                │
│                                                │
│  Acquire semaphore → call API                  │
│  Release semaphore on response/error           │
└───────────────────────────┬────────────────────┘
                            │
                            ▼
┌───────────────────────────────────────────────┐
│  API Call + Store                               │
│  - Call engine adapter                         │
│  - Store response in PostgreSQL                │
│  - Cache response in Redis                     │
│  - Release in-flight lock                      │
│  - Notify waiters via pub/sub                  │
└────────────────────────────────────────────────┘
```

---

## Component Deep Dives

### Component 1: AIEngineOrchestrator

This is the most architecturally critical component. It must handle parallel API calls with different rate limits, retries, and cost controls.

**Design: Adapter pattern + asyncio.Semaphore-based rate limiting**

```python
# backend/app/services/ai_engines/orchestrator.py

import asyncio
import hashlib
from typing import List, Dict
from datetime import datetime, timedelta

class AIEngineOrchestrator:
    """
    Dispatches queries to multiple AI engines in parallel.
    Handles rate limiting, caching, deduplication, retries.
    """

    def __init__(self, cache_service, db_session):
        self.cache = cache_service
        self.db = db_session

        # Per-engine concurrency semaphores
        self.semaphores = {
            "chatgpt": asyncio.Semaphore(3),
            "claude": asyncio.Semaphore(3),
            "perplexity": asyncio.Semaphore(5),
        }

        # Engine adapters (registered at init)
        self.adapters: Dict[str, BaseEngineAdapter] = {}

    async def execute_queries(
        self,
        queries: List[str],
        engines: List[str],
        cache_ttl_hours: int = 24
    ) -> List[AIEngineResponse]:
        """
        Execute all query x engine combinations in parallel.
        Returns list of AIEngineResponse objects.
        """
        tasks = []
        for query in queries:
            for engine in engines:
                tasks.append(
                    self._execute_single(query, engine, cache_ttl_hours)
                )

        # asyncio.gather with return_exceptions=True
        # so one failure doesn't cancel all others
        results = await asyncio.gather(*tasks, return_exceptions=True)

        responses = []
        for result in results:
            if isinstance(result, Exception):
                # Log error, create failed response record
                pass
            else:
                responses.append(result)

        return responses

    async def _execute_single(
        self, query: str, engine: str, cache_ttl_hours: int
    ) -> AIEngineResponse:
        """Single query to single engine with cache + rate limit."""

        cache_key = self._cache_key(query, engine)

        # 1. Cache check
        cached = await self.cache.get(cache_key)
        if cached:
            return cached

        # 2. Rate limit gate (semaphore)
        async with self.semaphores[engine]:
            # 3. Call adapter with retry
            adapter = self.adapters[engine]
            response = await adapter.query(query)

            # 4. Store + cache
            db_record = AIEngineResponse(
                query_text=query,
                engine_id=engine,
                response_text=response.text,
                model_used=response.model,
                tokens_used=response.tokens,
                latency_ms=response.latency_ms,
                cached=False,
                queried_at=datetime.utcnow(),
            )
            self.db.add(db_record)

            await self.cache.set(
                cache_key, db_record, ttl=timedelta(hours=cache_ttl_hours)
            )

            return db_record

    def _cache_key(self, query: str, engine: str) -> str:
        normalized = query.strip().lower()
        query_hash = hashlib.sha256(normalized.encode()).hexdigest()[:16]
        return f"ai_response:{engine}:{query_hash}"
```

**Why this design:**
- `asyncio.Semaphore` is the right primitive for per-engine concurrency limits. It is cooperative, lightweight, and handles backpressure naturally (callers wait, they do not fail).
- `asyncio.gather` with `return_exceptions=True` ensures one engine failure does not block results from other engines.
- Cache key uses normalized query hash, so "what is X?" and "What is X?" hit the same cache.
- Each engine adapter is independent and can be swapped, disabled, or rate-adjusted without touching orchestration logic.

### Component 2: Engine Adapters

```python
# backend/app/services/ai_engines/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class EngineResponse:
    text: str
    model: str
    tokens: int
    latency_ms: float
    raw_response: dict  # Full API response for debugging

class BaseEngineAdapter(ABC):
    """
    Each AI engine gets an adapter.
    Adapters handle auth, request formatting, response parsing,
    and retry logic specific to that engine's API.
    """

    @abstractmethod
    async def query(self, prompt: str) -> EngineResponse:
        """Send a query and return normalized response."""
        ...

    @abstractmethod
    def estimate_cost(self, prompt: str) -> float:
        """Estimate cost in USD for this query."""
        ...
```

```python
# backend/app/services/ai_engines/openai_adapter.py

import openai
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class OpenAIAdapter(BaseEngineAdapter):
    """ChatGPT adapter using OpenAI API."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.model = model

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((openai.RateLimitError, openai.APITimeoutError)),
    )
    async def query(self, prompt: str) -> EngineResponse:
        start = asyncio.get_event_loop().time()
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
            temperature=0.7,
        )
        latency = (asyncio.get_event_loop().time() - start) * 1000

        return EngineResponse(
            text=response.choices[0].message.content,
            model=response.model,
            tokens=response.usage.total_tokens,
            latency_ms=latency,
            raw_response=response.model_dump(),
        )

    def estimate_cost(self, prompt: str) -> float:
        # gpt-4o-mini: ~$0.15/1M input, ~$0.60/1M output
        estimated_tokens = len(prompt.split()) * 1.3 + 500  # rough estimate
        return estimated_tokens * 0.0000004
```

**Why `tenacity` for retries:** The library is already a standard in the Python ecosystem. It handles exponential backoff correctly and is composable with async. Using it instead of hand-rolled retry logic avoids off-by-one errors and edge cases around jitter, max wait, and exception filtering.

**Why `gpt-4o-mini` default:** Cost-effective for brand mention detection queries. A full audit generating 10 queries x 3 engines = 30 API calls. At gpt-4o-mini pricing this is roughly $0.01-0.03 per audit, versus $0.30-1.00 with gpt-4o. The audit is looking for factual mentions, not creative output, so the cheaper model is appropriate.

### Component 3: QueryGenerator

```python
# backend/app/services/query_generator.py

class QueryGenerator:
    """
    Crawls a URL, extracts brand/industry context,
    generates AI-relevant queries.
    """

    async def analyze_site(self, url: str) -> SiteContext:
        """
        Phase 1: Extract everything needed for query generation.
        Returns structured context about the brand.
        """
        # 1. Crawl with existing BeautifulSoup infrastructure
        # 2. Extract: brand name, meta description, product/service keywords
        # 3. Detect industry from content signals
        # 4. Find competitor mentions
        # 5. Check structured data (schema.org Organization, Product, etc.)
        ...

    async def generate_queries(self, context: SiteContext) -> List[Query]:
        """
        Phase 2: Generate queries that would reveal brand visibility in AI.

        Query categories:
        1. INDUSTRY: "What are the best [industry] tools/services?"
        2. BRAND_DIRECT: "What do you know about [brand_name]?"
        3. COMPARISON: "Compare [brand] vs [competitor]"
        4. PROBLEM: "How do I solve [problem brand solves]?"
        5. RECOMMENDATION: "Recommend a [product category] for [use case]"
        """
        # Use LLM to generate queries from site context
        # Template-based with LLM refinement for natural phrasing
        ...
```

**Why hybrid template + LLM for query generation:** Pure templates produce robotic queries that do not reflect how real users ask AI engines. Pure LLM generation is expensive and unreliable. The hybrid approach uses templates for structure (guaranteeing coverage of all query categories) and a single LLM call to refine phrasing.

### Component 4: ScoringPipeline

```python
# backend/app/services/scoring.py

class ScoringPipeline:
    """
    Two-dimensional scoring:
    1. Site Readiness (how well the site is optimized for AI)
    2. AI Presence (how visible the brand is in AI responses)
    Combined into a single 0-100 GEO Score.
    """

    # Site Readiness subscores (30% of final)
    SITE_WEIGHTS = {
        "structured_data": 0.25,    # schema.org, JSON-LD
        "content_quality": 0.25,    # depth, readability, E-E-A-T signals
        "ai_accessibility": 0.25,   # robots.txt allows AI crawlers, sitemap
        "authority_signals": 0.25,  # citations, expertise markers
    }

    # AI Presence subscores (70% of final)
    PRESENCE_WEIGHTS = {
        "mention_frequency": 0.30,    # How often brand appears across engines
        "mention_accuracy": 0.25,     # Does AI describe brand correctly?
        "sentiment": 0.15,            # Positive/neutral/negative
        "competitive_position": 0.20, # Brand rank vs competitors in responses
        "citation_quality": 0.10,     # Are sources cited? Is brand's URL linked?
    }

    def compute_final_score(
        self,
        site_signals: SiteAnalysis,
        ai_analysis: AIPresenceAnalysis
    ) -> AuditScore:
        site_score = self._compute_site_score(site_signals)
        presence_score = self._compute_presence_score(ai_analysis)

        final = int(site_score * 0.3 + presence_score * 0.7)

        return AuditScore(
            overall=final,
            site_readiness=site_score,
            ai_presence=presence_score,
            breakdown=self._generate_breakdown(site_signals, ai_analysis),
            gap_analysis=self._generate_gap_analysis(ai_analysis),
        )
```

**Why 70/30 weighting toward AI presence:** The product's core value proposition is "see how AI engines actually describe your brand." Site readiness matters (it influences future AI training data), but users are paying for the AI presence insights. A product that scores sites but never checks AI responses is what the old 108-point system did -- and that is what we are pivoting away from.

---

## Database Schema Design

### New Tables (Additions to Existing Schema)

```
audits
├── id                  UUID PK
├── website_id          UUID FK → websites
├── brand_name          String          -- Detected or user-provided
├── industry            String?         -- Auto-detected from site content
├── status              String          -- pending | site_analyzed | queries_generated |
│                                          ai_queried | responses_analyzed | completed | failed
├── overall_score       Integer?        -- 0-100 final GEO score
├── site_readiness_score Integer?       -- 0-100 site optimization score
├── ai_presence_score   Integer?        -- 0-100 AI visibility score
├── score_breakdown     JSONB?          -- Detailed sub-scores
├── gap_analysis        JSONB?          -- Competitor gaps, messaging mismatches
├── cost_usd            Float?          -- Total API cost for this audit
├── total_queries       Integer?        -- Number of AI queries sent
├── cached_queries      Integer?        -- Number served from cache
├── error_details       JSONB?          -- Error info if failed
├── created_at          DateTime
├── completed_at        DateTime?
└── requested_by        UUID? FK → profiles  -- null for unauthenticated MVP

audit_queries
├── id                  UUID PK
├── audit_id            UUID FK → audits
├── query_text          String          -- "What are the best CRM tools?"
├── query_category      String          -- industry | brand_direct | comparison |
│                                          problem | recommendation
├── query_hash          String(16)      -- sha256 prefix for cache key
├── is_user_custom      Boolean         -- false=auto-generated, true=user-added
├── created_at          DateTime

ai_engine_responses
├── id                  UUID PK
├── audit_id            UUID FK → audits
├── query_id            UUID FK → audit_queries
├── engine_id           String          -- chatgpt | claude | perplexity
├── model_used          String          -- gpt-4o-mini | claude-3.5-sonnet | etc.
├── response_text       Text            -- Full AI response
├── response_embedding  Vector(1536)    -- pgvector embedding for semantic comparison
├── tokens_used         Integer?
├── latency_ms          Float?
├── cost_usd            Float?          -- Estimated cost of this API call
├── cached              Boolean         -- Was this served from cache?
├── error_message       Text?           -- null if successful
├── queried_at          DateTime
├── INDEX               (query_id, engine_id) UNIQUE  -- One response per query per engine

brand_mentions
├── id                  UUID PK
├── response_id         UUID FK → ai_engine_responses
├── audit_id            UUID FK → audits    -- Denormalized for faster queries
├── brand_name          String          -- Which brand was mentioned
├── is_target_brand     Boolean         -- true = the brand being audited
├── mention_type        String          -- direct | indirect | comparison | recommendation
├── quote               Text            -- Exact quote from AI response
├── sentiment           String          -- positive | neutral | negative
├── position_in_response Integer?       -- 1=first mentioned, 2=second, etc.
├── context_text        Text?           -- Surrounding text for context
├── created_at          DateTime
├── INDEX               (audit_id, is_target_brand)
├── INDEX               (brand_name)    -- For cross-audit competitor tracking

site_crawl_results
├── id                  UUID PK
├── audit_id            UUID FK → audits
├── url                 String
├── page_title          String?
├── meta_description    Text?
├── detected_brand      String?         -- Brand name extracted from site
├── detected_industry   String?
├── detected_products   JSONB?          -- List of product/service keywords
├── detected_competitors JSONB?         -- Competitor names found on site
├── structured_data     JSONB?          -- schema.org data found
├── content_signals     JSONB?          -- readability, word count, heading structure
├── ai_crawler_access   JSONB?          -- robots.txt analysis for AI bots
├── raw_html_hash       String?         -- For detecting site changes over time
├── crawled_at          DateTime
```

### Schema Design Rationale

**Why `audits` as a separate table from existing `analyses`:** The existing `analyses` table stores the old scoring system (visibility/readability/authority from keyword matching). The new audits table is structurally different -- it orchestrates a multi-phase pipeline with AI API calls, has different scoring dimensions, and different status states. Reusing `analyses` would require a messy migration and confusion about which scoring system applies. Build the new system cleanly, then deprecate the old table.

**Why denormalize `audit_id` on `brand_mentions`:** The most common query pattern is "show me all brand mentions for this audit." Without denormalization, that requires JOIN through `ai_engine_responses`. With denormalization, it is a direct index scan. The data is write-once (mentions are computed once during analysis), so denormalization cost is minimal.

**Why `response_embedding` on `ai_engine_responses`:** Enables semantic comparison between what the AI says about the brand and what the site says about itself. This powers the "messaging alignment" feature. pgvector is already in the stack (used by Brand Voice), so no new infrastructure needed.

**Why `query_hash` on `audit_queries`:** Enables O(1) cache lookups. Two different audits asking "What are the best CRM tools?" should share cached responses. The hash is on the normalized (lowered, trimmed) query text.

### Relationship to Existing Tables

```
organizations ──┬── websites ──┬── analyses (OLD - keep for now, deprecate later)
                 │              └── audits (NEW)
                 │                    ├── audit_queries
                 │                    ├── ai_engine_responses
                 │                    │     └── brand_mentions
                 │                    └── site_crawl_results
                 │
                 └── brand_voice_configs (existing, keep as-is)
                       ├── voice_vectors
                       └── voice_rules
```

---

## Patterns to Follow

### Pattern 1: Phased Status Progression

**What:** The audit record progresses through well-defined status states. The frontend polls and renders progressively.

**Why:** An audit takes 30-120 seconds. Users need feedback during the wait. Phased status lets the frontend show "Crawling site..." then "Generating queries..." then "Querying AI engines (2/3 complete)..." instead of a blank spinner for 2 minutes.

```python
AUDIT_STATES = [
    "pending",              # Just created, queued for processing
    "site_analyzed",        # Site crawl complete, context extracted
    "queries_generated",    # AI queries generated
    "ai_queried",           # All AI engines responded
    "responses_analyzed",   # Brand mentions extracted, sentiment scored
    "completed",            # Final scores computed, report ready
    "failed",               # Error occurred (check error_details)
]
```

### Pattern 2: Adapter Registration

**What:** Engine adapters register with the orchestrator at startup. Adding a new AI engine means writing one adapter file and one registration line.

**Why:** Inevitably, new AI engines will matter (Gemini, Copilot, etc.). The system should not require refactoring to add one.

```python
# backend/app/services/ai_engines/__init__.py

from .openai_adapter import OpenAIAdapter
from .anthropic_adapter import AnthropicAdapter
from .perplexity_adapter import PerplexityAdapter

ENGINE_REGISTRY = {
    "chatgpt": OpenAIAdapter,
    "claude": AnthropicAdapter,
    "perplexity": PerplexityAdapter,
}
```

### Pattern 3: Cost Tracking Per Audit

**What:** Every API call records its estimated cost. The audit record aggregates total cost. This is not billing -- it is operational visibility.

**Why:** Without cost tracking, the first 1000 users could generate a surprise $500 API bill. Cost-per-audit lets you set guardrails (e.g., max $0.10 per audit for free tier, $0.50 for pro) and make pricing decisions based on real data.

### Pattern 4: Celery for the Audit Pipeline (not FastAPI BackgroundTasks)

**What:** Use Celery (already in docker-compose) for audit processing, not FastAPI's `BackgroundTasks`.

**Why:** The existing `AnalyzerService` uses `BackgroundTasks`, which runs in the same process as the web server. This works for the current 5-second analysis but will not work for 30-120 second AI audit pipelines that make external API calls. Celery runs in a separate worker process, handles retries natively, and survives web server restarts. The Celery worker is already declared in docker-compose but not wired to analysis -- this is the right time to wire it.

**Critical nuance:** Celery tasks are synchronous by default. For async AI API calls within a Celery task, use `asyncio.run()` inside the task function to run the async orchestrator. This is a well-established pattern -- Celery handles task dispatch and retry, asyncio handles concurrent API calls within a single task.

```python
# backend/app/tasks/audit_task.py

from celery import current_app
import asyncio

@current_app.task(bind=True, max_retries=2, soft_time_limit=300)
def run_audit_task(self, audit_id: str):
    """
    Celery task that runs the full audit pipeline.
    Uses asyncio.run() internally for concurrent AI API calls.
    """
    try:
        asyncio.run(_run_audit_async(audit_id))
    except Exception as exc:
        self.retry(exc=exc, countdown=30)

async def _run_audit_async(audit_id: str):
    # Full pipeline: crawl -> generate queries -> AI dispatch -> analyze -> score
    orchestrator = AuditOrchestrator(...)
    await orchestrator.run_full_audit(audit_id)
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Sequential AI API Calls

**What:** Calling ChatGPT, waiting for response, then calling Claude, waiting, then calling Perplexity.

**Why bad:** 3 engines x 10 queries = 30 calls. At 2-5s each, sequential execution = 60-150 seconds. Parallel execution with semaphores = 10-30 seconds (limited by the slowest engine's rate limit, not the sum of all calls).

**Instead:** `asyncio.gather()` with per-engine semaphores.

### Anti-Pattern 2: Storing AI Responses Only in JSONB

**What:** Dumping all AI responses into a single JSONB column on the audit record.

**Why bad:** Cannot query across audits ("show me all audits where ChatGPT mentioned brand X"), cannot do semantic search on responses, cannot efficiently compute trends over time.

**Instead:** Normalized tables: `ai_engine_responses` with proper columns + pgvector embedding, `brand_mentions` for extracted mentions.

### Anti-Pattern 3: Regenerating Queries for Every Audit of the Same Site

**What:** If a user audits the same URL twice in a week, crawling the site and generating queries from scratch each time.

**Why bad:** Wastes an LLM call for query generation and a site crawl. The site content probably has not changed.

**Instead:** Cache `site_crawl_results` by URL + date. If a crawl exists within 24 hours, reuse it. Let users force a fresh crawl if needed.

### Anti-Pattern 4: Blocking the API Response on Audit Completion

**What:** Making the POST /audit/start endpoint wait until the entire audit is done.

**Why bad:** HTTP timeout (60s typical) will kill the connection before the audit finishes. Frontend hangs. User refreshes and triggers duplicate audits.

**Instead:** Return `audit_id` immediately, process in Celery, frontend polls status. This is already the pattern used by the existing `POST /analyze` endpoint.

### Anti-Pattern 5: One Giant Service Class

**What:** Putting site crawling, query generation, AI dispatch, response analysis, and scoring all in one `AuditService` class.

**Why bad:** Violates single responsibility. Makes unit testing nearly impossible. Cannot evolve components independently (e.g., adding a new scoring dimension should not touch AI dispatch code).

**Instead:** Separate service classes per concern (QueryGenerator, AIEngineOrchestrator, ResponseAnalyzer, ScoringPipeline) coordinated by a thin AuditOrchestrator.

---

## File/Module Organization

```
backend/app/
├── api/
│   ├── audit.py                    # NEW: POST /audit/start, GET /audit/{id}, GET /audit/{id}/results
│   ├── analysis.py                 # KEEP: Legacy endpoint, deprecate later
│   └── ...existing...
│
├── services/
│   ├── audit_orchestrator.py       # NEW: Coordinates full audit flow
│   ├── query_generator.py          # NEW: Site crawl + query generation
│   ├── scoring.py                  # NEW: Scoring pipeline
│   ├── response_analyzer.py        # NEW: Brand mention extraction, sentiment
│   ├── ai_engines/                 # NEW: AI engine subsystem
│   │   ├── __init__.py             # Engine registry
│   │   ├── base.py                 # BaseEngineAdapter ABC
│   │   ├── orchestrator.py         # AIEngineOrchestrator (parallel dispatch)
│   │   ├── cache.py                # Redis cache layer for AI responses
│   │   ├── openai_adapter.py       # ChatGPT adapter
│   │   ├── anthropic_adapter.py    # Claude adapter
│   │   └── perplexity_adapter.py   # Perplexity adapter
│   ├── analyzer.py                 # KEEP: Legacy service, deprecate later
│   └── ...existing...
│
├── models/
│   ├── audit.py                    # NEW: Audit, AuditQuery, AIEngineResponse,
│   │                               #       BrandMention, SiteCrawlResult
│   └── ...existing...
│
├── schemas/
│   ├── audit.py                    # NEW: Pydantic request/response schemas
│   └── ...existing...
│
├── tasks/
│   ├── audit_task.py               # NEW: Celery task for audit pipeline
│   └── celery_app.py               # EXISTING: Wire audit_task here
│
└── core/
    └── ...existing (no changes needed)...
```

---

## Scalability Considerations

| Concern | At 100 users | At 10K users | At 1M users |
|---------|--------------|--------------|-------------|
| **AI API costs** | ~$3-10/day, no concern | ~$300-1000/day, need tiered limits + caching | Requires negotiated enterprise API pricing, aggressive caching |
| **Celery workers** | 1 worker, 4 concurrency | 3-5 workers, 16 concurrency total | Worker pool with auto-scaling, priority queues |
| **Response storage** | Single PostgreSQL, no issue | Partition `ai_engine_responses` by month, archive old data | Move historical responses to cold storage, keep recent in PostgreSQL |
| **Cache hit rate** | Low (few users, diverse queries) | Medium (agencies audit competing brands, queries overlap) | High (common industry queries cached across all users) |
| **Queue backlog** | No queue, immediate processing | Queue with priority (paid > free) | Multi-queue: express (paid), standard (free), batch (monitoring) |

**For MVP (current stage):** Single Celery worker with 4 concurrency threads is sufficient. 24-hour Redis cache on AI responses. No partitioning needed. Focus on correctness, not scale.

---

## Suggested Build Order

Dependencies determine build order. Components lower in this list depend on components above them.

```
Phase 1: Foundation                    Phase 2: Core Pipeline
─────────────────────────              ─────────────────────────
1a. Database models (audit.py)         2a. QueryGenerator
    - Audit, AuditQuery,                   - Site crawling (reuse existing
      AIEngineResponse,                      BeautifulSoup infrastructure)
      BrandMention,                        - Context extraction
      SiteCrawlResult                      - LLM-based query generation
    - Alembic migration
                                       2b. AIEngineOrchestrator
1b. Engine adapters                        - Parallel dispatch
    - BaseEngineAdapter ABC                - Cache integration
    - OpenAI adapter                       - Rate limit enforcement
    - Anthropic adapter
    - Perplexity adapter               2c. ResponseAnalyzer
    - Unit tests per adapter               - Brand mention detection
                                           - Sentiment analysis
1c. Redis cache service                    - Competitor extraction
    - Cache get/set with TTL               - pgvector alignment scoring
    - Query hash normalization
    - Cache invalidation

Phase 3: Scoring + API                 Phase 4: Frontend + Polish
─────────────────────────              ─────────────────────────
3a. ScoringPipeline                    4a. Audit results page
    - Site readiness scoring               - Score dashboard
    - AI presence scoring                  - AI mention cards with quotes
    - Gap analysis generation              - Gap analysis view
    - Score breakdown                      - Competitor comparison

3b. AuditOrchestrator                  4b. Audit initiation
    - Wire all components                  - URL input + options
    - Celery task integration              - Progress polling UI
    - Status progression                   - Cost estimation display

3c. API endpoints                      4c. Custom queries
    - POST /audit/start                    - User adds/edits queries
    - GET /audit/{id}                      - Query management UI
    - GET /audit/{id}/results
```

**Build order rationale:**

1. **Models first** because every other component depends on data structures. You cannot write services that store results without knowing the schema.
2. **Engine adapters before orchestrator** because the orchestrator needs adapters to compose. Adapters can be tested independently against real APIs (or mocks).
3. **Cache service early** because the orchestrator needs it, and it is simple to build (Redis get/set with TTL).
4. **QueryGenerator and AIEngineOrchestrator in Phase 2** because they are independent of each other and can be built in parallel by different developers.
5. **ResponseAnalyzer after AIEngineOrchestrator** because it needs real AI responses to process (cannot build without knowing what responses look like).
6. **ScoringPipeline after ResponseAnalyzer** because scoring depends on analyzed mentions and extracted data.
7. **AuditOrchestrator last in backend** because it wires everything together -- all components must exist first.
8. **Frontend last** because API endpoints must be stable before building UI against them.

**Vertical slice opportunity:** Build one complete path first (single query, single engine, basic scoring) end-to-end before expanding to multiple queries and engines. This validates the full pipeline with minimal investment.

---

## Integration with Existing Architecture

### What Stays Untouched
- Middleware stack (security headers, rate limiting, CORS, logging) -- applies to new endpoints automatically
- Database infrastructure (SQLAlchemy, Alembic, pgvector)
- Docker Compose setup (add env vars for new API keys, that is all)
- Frontend framework (Nuxt 3, Tailwind)
- Brand Voice module (independent, keep as-is)

### What Gets Extended
- **Settings** (`core/config.py`): Add `ANTHROPIC_API_KEY` (already present), `PERPLEXITY_API_KEY`, engine-specific rate limit configs
- **Celery** (`tasks/`): Wire `audit_task.py` -- the Celery worker already exists in docker-compose but is not connected to analysis
- **Models** (`models/__init__.py`): Register new model classes
- **API Router** (`main.py`): Register new `audit` router

### What Gets Deprecated (Not Removed)
- `POST /api/v1/analysis/analyze` -- keep working for backward compatibility, but new frontend points to `/audit/start`
- `AnalyzerService` -- the old keyword-in-headings scorer. Keep but do not extend.
- `geo_data_points/` -- the 108-point system. Some signals (structured data, robots.txt, readability) are reused in the site readiness score, but the orchestrator and scoring framework are replaced.

---

## Sources

- Existing codebase analysis: `/home/salim/Informatique/Perso/Endexa/geo-platform-mvp/.planning/codebase/ARCHITECTURE.md`
- Project definition: `/home/salim/Informatique/Perso/Endexa/geo-platform-mvp/.planning/PROJECT.md`
- Python asyncio.Semaphore: standard library pattern for cooperative concurrency limiting
- tenacity library: standard Python retry library (already commonly paired with OpenAI/Anthropic SDKs)
- OpenAI async client: `openai.AsyncOpenAI` supports native asyncio
- Anthropic async client: `anthropic.AsyncAnthropic` supports native asyncio
- Celery + asyncio pattern: `asyncio.run()` inside Celery task is the established bridge pattern

**Confidence notes:**
- HIGH confidence on architecture patterns (based on established Python async patterns and direct codebase analysis)
- HIGH confidence on schema design (based on the domain requirements and existing PostgreSQL + pgvector stack)
- MEDIUM confidence on specific API pricing (model pricing changes frequently; verify before hardcoding cost estimates)
- MEDIUM confidence on Perplexity API specifics (their API surface may have evolved; verify adapter interface against current docs)
