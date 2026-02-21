# Technology Stack: AI Brand Visibility Monitoring

**Project:** GEO Platform -- AI Brand Visibility Auditor
**Scope:** New capabilities for AI engine querying, brand presence analysis, and visibility scoring
**Researched:** 2026-02-21
**Overall Confidence:** MEDIUM (web verification tools unavailable; recommendations based on training data + codebase analysis. Flag versions for validation before implementation.)

---

## Existing Stack (Not Re-researched)

Already in the codebase and proven:

| Layer | Technology | Status |
|-------|-----------|--------|
| Backend | FastAPI 0.109+ (0.123.5 installed) | Working |
| Frontend | Nuxt 3 SPA | Working |
| Database | PostgreSQL 15 + pgvector | Working |
| Cache/Broker | Redis 7 | Working |
| ORM | SQLAlchemy 2.0.25 | Working |
| Task Queue | Celery 5.3.4 (5.6.0 installed) | Working |
| Crawling | Playwright + BeautifulSoup4 | Working |
| LLM (existing) | OpenAI SDK 1.7.0 (2.8.1 installed) | Working (optimizer.py) |
| LLM Abstraction | LiteLLM 1.17.0 (1.80.7 installed) | Listed but not used in code |
| Embeddings | pgvector + OpenAI text-embedding-3-small | Working (brand voice) |

---

## Recommended New Stack

### 1. AI Engine Query Layer -- Use LiteLLM as Unified Gateway

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **LiteLLM** | `>=1.40.0` (pin to latest stable) | Unified interface for all AI providers | Already in venv (1.80.7). Supports 100+ LLM providers through single `completion()` interface. OpenAI, Anthropic, Perplexity all supported. Eliminates per-provider SDK management. |

**Confidence:** HIGH -- LiteLLM is already installed (1.80.7) and supports all three target providers.

**Why LiteLLM instead of direct SDKs:**
- Already in the project (installed but unused -- the optimizer.py uses raw `openai` SDK instead)
- Single `litellm.completion()` call works for ChatGPT, Claude, and Perplexity
- Built-in retry logic, timeout handling, and fallback support
- Cost tracking per request (critical for per-audit cost monitoring)
- Provider-agnostic response format -- parse once, works for all

**Why NOT direct SDKs:**
- `openai` SDK: Already used in `optimizer.py` but locks you into OpenAI's interface. Would need separate `anthropic` SDK + Perplexity's OpenAI-compatible endpoint, meaning 3 different call patterns.
- `langchain`: Listed in requirements.txt but NOT installed in venv (correctly). Langchain adds massive dependency weight for what is essentially `completion()` calls. Overkill for this use case.

**Provider mapping in LiteLLM:**

```python
# ChatGPT -- use gpt-4o-mini for cost efficiency, gpt-4o for quality
litellm.completion(model="gpt-4o-mini", messages=[...])

# Claude -- use claude-3-5-haiku for cost efficiency, claude-3-5-sonnet for quality
litellm.completion(model="claude-3-5-haiku-20241022", messages=[...])

# Perplexity -- OpenAI-compatible, use sonar models for web-grounded answers
litellm.completion(model="perplexity/sonar", messages=[...])
```

**Required environment variables (add to config.py):**

```python
OPENAI_API_KEY: str          # Already exists
ANTHROPIC_API_KEY: str = ""  # Already exists
PERPLEXITY_API_KEY: str = "" # NEW -- add to Settings
```

---

### 2. AI Response Analysis -- NLP Stack for Brand Mention Detection

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **spaCy** | `>=3.7.0` | Named Entity Recognition (NER), text processing | Industry-standard NER. Detects brand names, organization names, product mentions in AI responses. Faster than LLM-based extraction for structured tasks. |
| **spaCy model: en_core_web_sm** | latest | English NER model (small, fast) | Good enough for brand/org name detection. Upgrade to `en_core_web_lg` if accuracy insufficient. |
| **rapidfuzz** | `>=3.6.0` | Fuzzy string matching | Catches brand mentions with typos, abbreviations, partial matches (e.g., "Microsoft Corp" matches "Microsoft"). Much faster than `fuzzywuzzy`. |
| **pgvector (existing)** | Already installed | Semantic similarity for response comparison | Compare AI responses semantically across engines. Already used for brand voice embeddings. |

**Confidence:** MEDIUM -- spaCy is well-established for NER. The specific approach (NER + fuzzy matching + embeddings) is a reasonable architecture but not verified against existing GEO tools.

**Why spaCy + rapidfuzz instead of pure LLM extraction:**
- Cost: Extracting brand mentions from 3 AI responses x 10 queries = 30 extractions per audit. Using an LLM for extraction adds significant cost on top of the query cost.
- Speed: spaCy NER runs in milliseconds vs. seconds for LLM extraction.
- Determinism: NER + fuzzy matching gives consistent results. LLM extraction can hallucinate or miss mentions inconsistently.
- LLM fallback: Use LLM extraction only for ambiguous cases where NER confidence is low.

**Why NOT:**
- `nltk` (already installed): Dated NER. spaCy is significantly better for entity recognition.
- `transformers` / `huggingface`: Heavy dependency for what NER + fuzzy matching handles well. Would need GPU for speed, which Docker Compose doesn't provide.
- Pure regex: Too brittle. Brand names appear in unexpected forms.

**Analysis pipeline pattern:**

```python
# 1. spaCy NER to find organization/product entities
# 2. rapidfuzz to match entities against target brand + known competitors
# 3. Contextual analysis: sentiment around mentions, citation position, recommendation vs. mention
# 4. pgvector semantic similarity to compare response quality across engines
# 5. LLM (gpt-4o-mini) for nuanced analysis only when NER is ambiguous
```

---

### 3. Query Auto-Generation -- LLM + Crawled Content

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **LiteLLM** (same as above) | Already recommended | Generate industry-relevant queries from crawled content | Use gpt-4o-mini to analyze crawled page content and generate search-style queries a user might ask an AI engine about this industry/brand. |
| **BeautifulSoup4 (existing)** | Already installed | Extract page content, headings, meta data | Already used by AnalyzerService. Reuse for query generation context. |
| **tiktoken (existing)** | Already installed | Token counting for prompt construction | Ensure crawled content fits within context window when building query generation prompts. |

**Confidence:** MEDIUM -- Using LLMs to generate search queries from content is a well-established pattern, but the specific prompt engineering needs iteration.

**Why LLM-based query generation instead of keyword extraction:**
- AI engines respond to natural language questions, not keywords. Generating "What is the best CRM for small businesses?" is more valuable than extracting "CRM small business".
- Context-aware: LLM understands the page topic and generates queries that a real user would ask an AI engine.
- Industry-aware: Can generate competitor-comparison queries ("X vs Y") and buying-intent queries that are highly relevant for brand visibility.

**Query generation approach:**

```python
# Input: Crawled page content (title, headings, meta description, body text truncated to fit context)
# Prompt: "Based on this website content, generate 10-15 industry-relevant questions
#          that a user might ask an AI assistant. Include:
#          - Direct brand queries (e.g., 'What is [Brand]?')
#          - Industry queries (e.g., 'Best [industry category] tools')
#          - Comparison queries (e.g., '[Brand] vs [competitor]')
#          - Problem-solving queries (e.g., 'How to solve [problem brand addresses]')
#          Return JSON array of queries with category labels."
# Model: gpt-4o-mini (sufficient quality, low cost)
```

---

### 4. Cost-Efficient API Call Patterns

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **LiteLLM Budget Manager** | Built into LiteLLM | Per-user/per-audit cost tracking | LiteLLM tracks cost per completion call. Use to enforce per-audit budgets and display cost to user. |
| **Redis (existing)** | Already installed | Response caching | Cache AI responses by (query, engine, date) tuple. Same query to same engine within 24h returns cached result. |
| **Celery (existing)** | Already installed | Async batch processing | Fan out 3 engines x N queries as Celery tasks. Process in parallel with configurable concurrency. |
| **asyncio + httpx (existing)** | Already installed | Concurrent API calls within a single task | Use `asyncio.gather()` to send multiple queries to different engines simultaneously. |

**Confidence:** HIGH for the patterns, MEDIUM for specific LiteLLM budget features (need version verification).

**Cost optimization strategies:**

| Strategy | Savings | Implementation |
|----------|---------|----------------|
| **Response caching** | 70-90% on repeat audits | Redis cache with 24h TTL per (query, engine) pair. Brand monitoring re-checks only query engines if cache expired. |
| **Model tiering** | 50-80% per call | Use cheapest adequate model per task: gpt-4o-mini for query generation, claude-3-5-haiku for Claude queries, perplexity/sonar for Perplexity. Reserve gpt-4o/claude-3-5-sonnet for deep analysis. |
| **Batch queries per engine** | 20-30% latency reduction | Group all queries for one engine into a batch. OpenAI Batch API gives 50% cost discount for async (24h window) jobs. |
| **Token-aware prompts** | 10-20% per call | Use tiktoken to measure prompt size. Truncate crawled content to fit context efficiently. Avoid sending full page body when headings + meta suffice. |
| **Smart query deduplication** | Variable | Before querying, deduplicate semantically similar queries using pgvector cosine similarity. Threshold of 0.92+ similarity = skip duplicate. |

**Estimated cost per audit (10 queries x 3 engines):**

| Component | Model | Estimated Cost |
|-----------|-------|----------------|
| Query generation | gpt-4o-mini | ~$0.002 |
| ChatGPT queries (10) | gpt-4o-mini | ~$0.01-0.03 |
| Claude queries (10) | claude-3-5-haiku | ~$0.005-0.015 |
| Perplexity queries (10) | sonar | ~$0.01-0.03 (per-request pricing) |
| Response analysis | gpt-4o-mini (for ambiguous cases only) | ~$0.005 |
| **Total per audit** | | **~$0.03-0.08** |

**IMPORTANT cost note:** Perplexity's API pricing is per-request rather than per-token for some models. Verify current pricing before implementation. OpenAI Batch API provides 50% discount but has 24h turnaround -- useful for scheduled monitoring, not real-time audits.

---

### 5. OpenAI Batch API -- For Scheduled Monitoring (v2 Feature)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **OpenAI Batch API** | Available via openai SDK | 50% cost reduction for non-urgent queries | For the paid monitoring/re-check feature, batch all ChatGPT queries and submit via Batch API. Results return within 24h at half price. |

**Confidence:** MEDIUM -- OpenAI Batch API was available as of early 2025. Verify it is still offered and pricing hasn't changed.

**When to use:**
- Scheduled brand monitoring (daily/weekly re-checks) -- YES, use Batch API
- Real-time one-off audits -- NO, use standard API for immediate response

---

### 6. Existing GEO/AI Visibility Tools and Libraries

| Tool | What It Is | Relevance | Recommendation |
|------|-----------|-----------|----------------|
| **No established open-source library** | The GEO/AI visibility monitoring space is nascent (2024-2026). No mature open-source library exists. | High relevance -- means building custom. | Build custom. This is a competitive advantage, not a commodity. |
| **Otterly.ai** | Commercial GEO monitoring SaaS | Competitor, not a library. | Study their feature set for table-stakes validation, but build your own engine. |
| **Peec AI** | Commercial AI visibility monitoring | Competitor. | Same as above. |
| **Profound** | AI search analytics platform | Competitor. | Same as above. |

**Confidence:** LOW -- I could not verify the current landscape with web search. The GEO tools space is evolving rapidly. There may be new open-source libraries or APIs that launched after my training cutoff.

**RESEARCH GAP:** Verify whether any open-source Python libraries for AI visibility monitoring have been released in late 2025 or 2026. Search for: "GEO monitoring library python", "AI brand visibility open source", "LLM search monitoring tool".

---

## Complete New Dependencies

### Python packages to ADD to `requirements.txt`:

```bash
# AI Engine Query Layer (LiteLLM already installed, but pin to modern version)
litellm>=1.40.0      # UPDATE from 1.17.0 -- needed for latest provider support

# NLP / Brand Mention Analysis
spacy>=3.7.0          # Named Entity Recognition for brand detection
rapidfuzz>=3.6.0      # Fast fuzzy string matching for brand name variants

# Already installed, no changes needed:
# openai (via litellm dependency)
# tiktoken (already listed)
# httpx (already listed)
# redis (already listed)
# celery (already listed)
# beautifulsoup4 (already listed)
# pgvector (already listed)
```

### Post-install step:

```bash
# Download spaCy English model
python -m spacy download en_core_web_sm
```

### Python packages to REMOVE from `requirements.txt`:

```bash
# REMOVE -- not installed, not needed, adds confusion
langchain==0.1.0         # Not installed in venv. LiteLLM handles all LLM calls.
langchain-openai==0.0.2  # Not installed in venv. Dead dependency.
sentence-transformers==2.2.2  # Not installed in venv. OpenAI embeddings used instead.
```

### Config changes (add to `backend/app/core/config.py` Settings class):

```python
# New AI Engine API Keys
PERPLEXITY_API_KEY: str = ""

# AI Query Configuration
AI_QUERY_CACHE_TTL: int = 86400          # 24 hours in seconds
AI_QUERY_MAX_PER_AUDIT: int = 15         # Max queries per audit
AI_QUERY_TIMEOUT: int = 30               # Seconds per AI API call
AI_QUERY_MAX_RETRIES: int = 3            # Retries per failed call
AI_QUERY_CONCURRENCY: int = 5            # Max concurrent API calls

# Cost Controls
AI_AUDIT_MAX_COST: float = 0.50          # Max cost per audit in USD
AI_MONTHLY_BUDGET: float = 100.0         # Monthly budget cap in USD

# Model Selection (override per environment)
AI_QUERY_MODEL_OPENAI: str = "gpt-4o-mini"
AI_QUERY_MODEL_ANTHROPIC: str = "claude-3-5-haiku-20241022"
AI_QUERY_MODEL_PERPLEXITY: str = "perplexity/sonar"
AI_ANALYSIS_MODEL: str = "gpt-4o-mini"   # For response analysis
AI_QUERYGEN_MODEL: str = "gpt-4o-mini"   # For query generation
```

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| LLM Gateway | LiteLLM | Direct SDKs (openai, anthropic) | 3 different call patterns, no unified cost tracking, more code to maintain. LiteLLM already installed. |
| LLM Gateway | LiteLLM | LangChain | Massive dependency, overkill for completion calls, not installed despite being in requirements.txt. |
| NER | spaCy | Hugging Face transformers | Heavy (needs torch), no GPU in Docker Compose, spaCy is lighter and fast enough. |
| NER | spaCy | Pure regex/keyword matching | Too brittle. Brands appear as abbreviations, misspellings, partial names. |
| NER | spaCy | LLM-based extraction for every response | Too expensive at scale (30+ extractions per audit), too slow, non-deterministic. |
| Fuzzy Matching | rapidfuzz | fuzzywuzzy | rapidfuzz is a drop-in replacement that is 10-100x faster (C++ backend vs pure Python). |
| Fuzzy Matching | rapidfuzz | thefuzz | thefuzz is just fuzzywuzzy renamed. Same performance issues. |
| Response Caching | Redis (existing) | PostgreSQL JSONB | Redis is faster for TTL-based caching. PostgreSQL for persistent storage of historical results. Use both: Redis for cache, PostgreSQL for audit history. |
| Batch Processing | Celery (existing) | asyncio only | Celery provides task persistence, retry, monitoring via Flower. Pure asyncio loses tasks on crash. |
| Cost Tracking | LiteLLM built-in | Custom tracking | LiteLLM already calculates cost per call. No need to build custom. |
| Query Generation | LLM (gpt-4o-mini) | KeyBERT / YAKE keyword extraction | Keywords are not questions. AI engines need natural language queries, not keyword lists. |

---

## Architecture Integration Points

### How new components fit into existing 4-layer architecture:

```
Existing Layer          New Addition
--------------          ---------------
Routers (API)    -->    /api/v1/ai-audit/* (new router)
                        /api/v1/queries/* (new router for query management)

Services         -->    AIQueryService (orchestrates multi-engine queries)
                        BrandAnalyzer (NER + fuzzy matching + semantic analysis)
                        QueryGenerator (LLM-based query creation from crawled content)
                        VisibilityScorer (aggregates brand presence into 0-100 score)

Models           -->    AIQuery (stores generated/custom queries)
                        AIResponse (stores raw AI engine responses)
                        BrandMention (extracted mentions with context)
                        VisibilityScore (per-engine and aggregate scores)

Tasks (Celery)   -->    run_ai_audit (orchestrator task)
                        query_ai_engine (per-engine subtask)
                        analyze_responses (post-query analysis)
```

### Data flow for a single audit:

```
1. User submits URL
2. Celery: Crawl URL (existing BeautifulSoup/Playwright)
3. Celery: QueryGenerator creates 10-15 queries from crawled content
4. Celery: Fan out queries to 3 engines via LiteLLM (parallel, cached)
5. Celery: BrandAnalyzer processes all responses (spaCy NER + rapidfuzz)
6. Celery: VisibilityScorer computes per-engine and aggregate scores
7. Store results in PostgreSQL (AIResponse, BrandMention, VisibilityScore)
8. Frontend polls and displays results
```

---

## Version Verification Checklist

**IMPORTANT:** The following versions need verification against official docs before pinning in requirements.txt. Web verification was unavailable during this research.

| Package | Recommended | Verify At | What to Check |
|---------|-------------|-----------|---------------|
| litellm | `>=1.40.0` | https://github.com/BerriAI/litellm/releases | Latest stable, Perplexity support status |
| spacy | `>=3.7.0` | https://spacy.io/usage | Latest stable, Python 3.12 compatibility |
| rapidfuzz | `>=3.6.0` | https://pypi.org/project/rapidfuzz/ | Latest stable |
| Perplexity models | `perplexity/sonar` | https://docs.perplexity.ai/ | Current model names, pricing, rate limits |
| OpenAI models | `gpt-4o-mini` | https://platform.openai.com/docs/models | Current model names, pricing |
| Anthropic models | `claude-3-5-haiku-20241022` | https://docs.anthropic.com/en/docs/about-claude/models | Current model names, pricing, latest snapshot dates |
| OpenAI Batch API | 50% discount claim | https://platform.openai.com/docs/guides/batch | Verify still available and pricing unchanged |

---

## Migration Path from Current Code

### optimizer.py needs refactoring:

**Current** (lines 4-7, 54):
```python
import openai
openai.api_key = settings.OPENAI_API_KEY
# ...
response = openai.chat.completions.create(model="gpt-4o-mini", ...)
```

**Target:**
```python
import litellm
# No global API key setup -- LiteLLM reads from env vars automatically
# ...
response = litellm.completion(model="gpt-4o-mini", messages=[...])
```

This migration is low-risk because LiteLLM's `completion()` returns an OpenAI-compatible response object. The rest of the code (parsing `response.choices[0].message.content`) stays the same.

### requirements.txt cleanup:

Remove langchain, langchain-openai, sentence-transformers (not installed, not needed).
Update litellm pin from 1.17.0 to >=1.40.0.
Add spacy, rapidfuzz.

---

## Sources and Confidence

| Claim | Source | Confidence |
|-------|--------|------------|
| LiteLLM supports OpenAI, Anthropic, Perplexity | Training data + codebase (1.80.7 installed) | HIGH |
| LiteLLM `completion()` is OpenAI-response-compatible | Training data (well-established) | HIGH |
| spaCy NER is effective for organization/brand name extraction | Training data (well-established NLP library) | HIGH |
| rapidfuzz is faster than fuzzywuzzy | Training data (well-established benchmark) | HIGH |
| Perplexity API is OpenAI-compatible format | Training data (established as of early 2025) | MEDIUM |
| Perplexity model name is "sonar" | Training data (was accurate as of early 2025) | MEDIUM -- verify |
| OpenAI Batch API provides 50% discount | Training data (was accurate as of mid-2024) | MEDIUM -- verify |
| Claude 3.5 Haiku model identifier | Training data | MEDIUM -- verify snapshot date |
| gpt-4o-mini pricing estimates | Training data | LOW -- pricing changes frequently |
| No established open-source GEO monitoring library | Training data only, could not search | LOW -- verify |
| Cost-per-audit estimate ($0.03-0.08) | Calculated from training-data pricing | LOW -- verify against current pricing |

**Overall assessment:** The architectural recommendations (LiteLLM as gateway, spaCy + rapidfuzz for NER, Celery for orchestration, Redis for caching) are HIGH confidence. The specific model names, pricing, and version numbers are MEDIUM-LOW confidence and should be verified against live documentation before implementation.
