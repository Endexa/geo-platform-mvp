# Architecture Patterns

**Domain:** GEO/SEO SaaS Platform -- v2 Rebuild
**Researched:** 2026-02-25
**Confidence:** HIGH (based on codebase audit + existing working infrastructure)

## Executive Summary

The existing FastAPI + Celery + Supabase architecture is sound (70/100 architecture grade per audit critique). The rebuild adds 9 major components to this foundation. The critical insight is that **nearly every new feature depends on the scoring pipeline producing real data**, making it the single most important prerequisite. The architecture should be organized around an "Audit" as the central aggregate, with all new features (recommendations, chat, reports, payments, competitors) radiating from it.

This document maps each new component, defines boundaries, specifies data flows, and recommends a build order based on hard dependencies.

---

## Recommended Architecture

### System Overview

```
                    +------------------+
                    |   Nuxt 3 SPA     |
                    |  (Vue 3 + TW)    |
                    +--------+---------+
                             |
                    REST API + WebSocket
                             |
                    +--------+---------+
                    |   FastAPI App     |
                    |  (main.py)        |
                    +--------+---------+
                             |
              +--------------+--------------+
              |              |              |
     +--------+------+ +----+----+ +-------+--------+
     |  Celery Worker | |  Redis  | | Supabase PG    |
     |  (audit pipe)  | | (cache/ | | (data + pgvec) |
     +--------+------+ | broker) | +-------+--------+
              |         +----+----+         |
     +--------+------+                     |
     |  AI Engines    |                     |
     |  (LiteLLM)     |                     |
     +----------------+                     |
                                            |
     +----------------+                     |
     |  Stripe API    +---------------------+
     +----------------+
```

### Component Boundaries

| Component | Responsibility | Communicates With | Build Phase |
|-----------|---------------|-------------------|-------------|
| **ScoringPipeline** | Run 61 criteria against crawled pages, produce real measurements | CrawlerService, DB (CriterionResult, PageScore) | Phase 1 (FIRST) |
| **RecommendationEngine** | Gap analysis, priority ordering, code snippets, action steps | ScoringPipeline output, CompetitorAudit data, DB | Phase 2 |
| **ChatAssistant** | WebSocket-based Q&A over audit results | FastAPI WebSocket, LiteLLM, DB (audit data) | Phase 4 |
| **ReportGenerator** | PDF/HTML export of audit results + recommendations | DB (all audit data), WeasyPrint, Jinja2 | Phase 3 |
| **PaymentGating** | Stripe subscriptions, freemium feature gating | Stripe API, DB (Organization.subscription_tier) | Phase 3 |
| **CompetitorBenchmarking** | Crawl + score competitor sites, share-of-voice | CrawlerService, ScoringPipeline, EntityExtractor | Phase 2 |
| **CodeAnalysisFlow** | Generate prompts for user's AI tools, ingest output | DB (audit data), dedicated API endpoints | Phase 4 |
| **JiraCSVExport** | Export recommendations as importable CSV | DB (AuditRecommendation), pandas/csv module | Phase 3 |
| **ProductionDashboard** | Real metrics, trend charts, audit history | DB (all tables), Nuxt 3 composables, Chart.js | Phase 5 |

---

## Data Model: The Audit Aggregate

The `Audit` is the central aggregate root. Every feature radiates from it:

```
                            Audit
                              |
            +---------+-------+-------+---------+
            |         |       |       |         |
        AuditQuery  PageScore  VisibilityScore  Brand
            |         |
    EngineResponse  CriterionResult
            |
    BrandMention    AuditRecommendation
            |
    MentionSentiment  DiscoveredCompetitor
                            |
                      CompetitorAudit

    NEW TABLES (to add):
    - ChatSession (audit_id FK, messages JSONB, created_at)
    - AuditReport (audit_id FK, format, file_url, created_at)
    - Subscription (user_id FK, stripe_customer_id, tier, status, current_period_end)
    - CodeAnalysisPrompt (audit_id FK, prompt_text, status)
    - CodeAnalysisResult (prompt_id FK, output_text, parsed_findings JSONB)
```

### Existing Tables (19 total, keep as-is)

| Table | Records per Audit | Status |
|-------|-------------------|--------|
| `audits` | 1 | Working |
| `audit_queries` | 10-15 | Working |
| `engine_responses` | 40-60 (queries x engines) | Working |
| `brand_mentions` | 0-50+ | Working |
| `visibility_scores` | 1 | Working |
| `page_scores` | 5-10 (configurable cap) | Working |
| `criterion_results` | 61 x pages_scored | Framework exists, criteria return 0 |
| `audit_recommendations` | 10-40 | Framework exists, needs real scoring data |
| `discovered_competitors` | 5-15 | Working |
| `competitor_audits` | 3-5 | Working |
| `mention_sentiments` | per mention | Working |
| `audit_cost_ledger` | per API call | Working |
| `profiles` | per user | Working |
| `organizations` | per org | Working |
| `brands` | per brand | Working |
| `websites` | per site | Exists |
| `brand_voice_*` | per config | Exists (deferred to v3) |
| `analyses` | legacy | Exists (legacy, to deprecate) |
| `recommendations` | legacy | Exists (legacy, to deprecate) |

### New Tables (5 to add)

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `chat_sessions` | Persist chat conversations per audit | `audit_id`, `messages` (JSONB array), `model_used`, `token_count` |
| `audit_reports` | Track generated reports | `audit_id`, `format` (pdf/html), `storage_path`, `generated_at` |
| `subscriptions` | Stripe subscription state (replaces org.subscription_tier) | `user_id`, `stripe_subscription_id`, `tier`, `status`, `current_period_end` |
| `code_analysis_prompts` | Prompts generated for user's AI tools | `audit_id`, `prompt_text`, `target_files`, `status` |
| `code_analysis_results` | User-uploaded output from running prompts | `prompt_id`, `raw_output`, `parsed_findings` (JSONB), `uploaded_at` |

---

## Component Detail: Data Flows

### 1. Scoring Pipeline (CRITICAL PATH)

**Current state:** 4 category scorers registered (crawlability, content_structure, structured_data, authority). Criteria exist as framework but most return score=0.

**Target state:** All 61 criteria produce real measurements from crawl data.

```
Data Flow:
  CrawlerService.crawl(url)
    -> CrawlResult (html, headings, schema_org, ai_bot_access, ...)
      -> ScoringOrchestrator.score_audit()
        -> CrawlerService.crawl_multiple(discovered_pages)
        -> For each page:
          -> CrawlabilityScorer.score_page(page_data)   -> [CriterionResult x 12]
          -> ContentStructureScorer.score_page(page_data) -> [CriterionResult x 13]
          -> StructuredDataScorer.score_page(page_data)   -> [CriterionResult x 13]
          -> AuthorityScorer.score_page(page_data)        -> [CriterionResult x 23]
        -> Store PageScore + CriterionResult records
        -> Weakest-link aggregation -> optimization_score
```

**Key Pattern: Score from Crawl Data Only**

Each scorer receives a `page_data` dict (the CrawlResult serialized) and must extract all signals from it. No additional HTTP calls inside scorers. The crawler is responsible for fetching everything needed.

**Implication:** The CrawlerService may need enrichment to capture data that scorers need but don't currently receive (e.g., full HTML for structured data parsing, response headers for TTFB, Lighthouse-style metrics). This is a Phase 1 prerequisite.

```python
# Pattern: BaseScorer interface (already exists)
class BaseScorer:
    async def score_page(self, page_data: dict) -> list[ScoringCriterionResult]:
        """Each criterion returns: criterion_id, score 0-100, human_summary, evidence"""
        ...

    def compute_category_score(self, results: list[ScoringCriterionResult]) -> float:
        """Weighted average of criterion scores within category"""
        ...
```

### 2. Recommendation Engine

**Current state:** Deterministic gap analysis engine exists and works. Compares user scores against competitor averages and research benchmarks. Produces AuditRecommendation records with evidence, code snippets, and action steps.

**Target state:** Keep deterministic engine. Enhance with richer code snippets, industry-specific recommendations, and better prioritization once scoring produces real data.

```
Data Flow:
  ScoringPipeline completes
    -> RecommendationEngine.generate_recommendations(audit_id)
      -> Load CriterionResult records (per page)
      -> Load CompetitorAudit category averages
      -> For each criterion below threshold:
        -> Compute gap_score (competitor_avg - user_score OR benchmark - user_score)
        -> Classify priority (HIGH/MEDIUM/LOW based on impact_pct + gap_score)
        -> Attach code_snippet from CRITERION_SNIPPETS map
        -> Carry over prior done/dismissed status via recommendation_hash
      -> Generate sentiment-based recommendations for negative mentions
      -> Identify content gaps (queries where competitors appear, user doesn't)
      -> Store AuditRecommendation records
      -> Store content_gaps on Audit.content_gaps JSONB
```

**Key Insight:** The recommendation engine is NOT LLM-based. It is deterministic. This is correct -- deterministic recommendations are reproducible, testable, and don't incur API costs. LLM involvement should be limited to the chat assistant (where users ask follow-up questions about recommendations).

### 3. Chat Assistant

**Architecture: WebSocket + LiteLLM streaming**

The chat assistant allows users to ask questions about their audit results. It uses the audit data as context and streams LLM responses.

```
Data Flow:
  User opens chat panel on audit detail page
    -> Frontend establishes WebSocket connection to /ws/chat/{audit_id}
    -> Backend authenticates via JWT token in connection params
    -> Backend loads audit context:
      - Audit.crawl_data (summarized)
      - Top 10 AuditRecommendation records
      - VisibilityScore breakdown
      - CriterionResult scores by category
      - ContentGaps
    -> Context injected as system prompt
    -> User sends message
    -> Backend streams LiteLLM response token-by-token via WebSocket
    -> Chat history stored in chat_sessions table (JSONB messages array)
    -> Budget cap: X messages per audit (freemium gating)
```

**Implementation Pattern:**

```python
# FastAPI WebSocket endpoint
@router.websocket("/ws/chat/{audit_id}")
async def chat_websocket(
    websocket: WebSocket,
    audit_id: str,
    db: Session = Depends(get_db),
):
    await websocket.accept()
    # Authenticate, load context, stream responses
    # Use litellm.acompletion(..., stream=True) for token streaming
    async for chunk in response:
        await websocket.send_text(chunk.choices[0].delta.content or "")
```

**Key Decision: WebSocket over SSE.** WebSocket is bidirectional, allowing the user to cancel generation or send follow-ups while the LLM is still responding. SSE is simpler but one-directional. For a chat experience, WebSocket is the right choice.

**Context Window Management:** Summarize audit data to fit within context limits. Use a template that includes: overall scores, top 5 failing criteria, top 3 recommendations, content gaps summary. Full audit data would exceed context limits for large audits.

### 4. Report Generation (PDF/HTML)

**Architecture: Jinja2 templates + WeasyPrint**

```
Data Flow:
  User clicks "Export Report" on audit detail page
    -> POST /api/v1/reports/{audit_id}/generate?format=pdf
    -> Celery task: generate_report(audit_id, format)
      -> Load all audit data from DB
      -> Render Jinja2 HTML template with data
      -> If format=pdf: WeasyPrint converts HTML to PDF
      -> If format=html: Return rendered HTML directly
      -> Store file reference in audit_reports table
      -> Return download URL
    -> Frontend polls or uses WebSocket notification for completion
    -> User downloads generated file
```

**Key Decision: Celery task, not synchronous endpoint.** PDF generation with WeasyPrint can take 5-15 seconds for complex reports. Running it in a Celery worker prevents blocking API threads.

**Template Structure:**

```
report_template.html.j2
  - Cover page (brand, domain, date, overall scores)
  - Executive Summary (scores by category, visibility breakdown)
  - Per-Category Detail (criterion results, evidence, charts)
  - Recommendations (priority-ordered, with code snippets)
  - Competitor Benchmarking (leaderboard, score comparison)
  - Content Gaps (topics to address)
  - Appendix (methodology, scoring weights, data sources)
```

**Styling:** CSS in the Jinja2 template, using Tailwind-inspired utility classes that WeasyPrint supports. Charts rendered as inline SVG (not Chart.js canvas -- WeasyPrint can't execute JS).

### 5. Stripe Payment + Freemium Gating

**Current state:** Stub endpoints exist in `integrations.py`. Checkout session creation and webhook handling are partially implemented but use the legacy `Organization` model.

**Target state:** Working subscription management with three tiers and feature gating middleware.

```
Data Flow:
  User clicks "Upgrade" on pricing page
    -> POST /api/v1/payments/create-checkout
      -> Create Stripe Checkout Session with price_id for selected tier
      -> Return checkout_url
    -> User completes payment on Stripe-hosted checkout
    -> Stripe fires webhook: checkout.session.completed
      -> POST /api/v1/payments/webhook (public, signature-verified)
        -> Update subscriptions table (tier, status, stripe_subscription_id)
        -> Log event

  Feature gating (on every gated request):
    -> Middleware or dependency reads user's subscription tier
    -> Tier determines: max audits/month, AI query budget, report export, chat messages
    -> Return 402 Payment Required if over limit
```

**Freemium Tier Structure:**

| Feature | Free | Pro ($49/mo) | Team ($149/mo) |
|---------|------|-------------|----------------|
| Audits/month | 3 | 20 | Unlimited |
| Pages per audit | 3 | 10 | 50 |
| AI engines | 2 (Gemini + Perplexity) | All 4 | All 4 |
| Recommendations | Top 5 only | All | All |
| PDF report | No | Yes | Yes |
| Chat messages | 5/audit | 50/audit | Unlimited |
| Competitor benchmarking | No | 3 competitors | 10 competitors |
| Code analysis | No | Yes | Yes |
| Jira CSV export | No | Yes | Yes |
| Team members | 1 | 1 | 5 |

**Gating Implementation Pattern:**

```python
# Dependency injection for tier checking
from enum import IntEnum

class SubscriptionTier(IntEnum):
    FREE = 0
    PRO = 1
    TEAM = 2

def require_tier(minimum: SubscriptionTier):
    async def dependency(current_user: Profile = Depends(get_current_active_user), db: Session = Depends(get_db)):
        subscription = db.query(Subscription).filter(Subscription.user_id == current_user.id).first()
        tier = SubscriptionTier[subscription.tier.upper()] if subscription else SubscriptionTier.FREE
        if tier < minimum:
            raise HTTPException(status_code=402, detail="Upgrade required")
        return tier
    return dependency

# Usage:
@router.get("/reports/{audit_id}/download")
async def download_report(
    audit_id: str,
    tier: SubscriptionTier = Depends(require_tier(SubscriptionTier.PRO)),
):
    ...
```

### 6. Competitor Benchmarking

**Current state:** Entity extraction from AI responses works. URL resolution and competitor crawling partially implemented. CompetitorAudit model stores results.

**Target state:** Reliable competitor discovery, URL resolution, parallel crawl+score, leaderboard with share-of-voice.

```
Data Flow:
  Audit pipeline Stage 6 (DISCOVERING_COMPETITORS):
    -> EntityExtractorService.discover_competitors_for_audit()
      -> NER on engine responses -> DiscoveredCompetitor records
      -> Share-of-voice calculation (mention_count / total_mentions)
    -> CompetitorService.crawl_top_competitors()
      -> Resolve entity names to URLs (WebSearch or domain heuristics)
      -> CrawlerService.crawl(competitor_url) for top 3-5
      -> ScoringOrchestrator.score_audit() on each (reuse same scorers)
      -> Store CompetitorAudit with per-category averages
    -> RecommendationEngine uses competitor averages for gap analysis

  Leaderboard API:
    -> GET /api/v1/competitors/{audit_id}/leaderboard
      -> Returns all entities ranked by share_of_voice
      -> Includes optimization scores for crawled competitors
      -> Highlights user brand position in ranking
```

**Key Risk:** URL resolution (brand name -> website URL) is unreliable. Mitigation: Use multiple signals (web search, domain guessing, cached mappings from prior audits), and always show users which competitors were identified so they can correct mistakes.

### 7. Code Analysis Flow

**Architecture: Prompt generation + output ingestion (no direct repo access)**

This is the "Shannon-style" approach from the critique: generate prompts that users run on their own repos using their AI tools (Copilot, Cursor, Claude Code), then upload the output back to Endexa.

```
Data Flow:
  Phase A -- Prompt Generation:
    Audit completes
      -> POST /api/v1/code-analysis/{audit_id}/generate-prompts
        -> Analyze audit findings (failing criteria, recommendations)
        -> Generate targeted prompts:
          - "Check if SSR is enabled in your build config"
          - "Find all pages without meta descriptions"
          - "List all JSON-LD schema in your codebase"
          - "Analyze your robots.txt and sitemap.xml"
        -> Store in code_analysis_prompts table
        -> Return prompts to user (copy-paste ready)

  Phase B -- Output Ingestion:
    User runs prompts on their codebase, copies output
      -> POST /api/v1/code-analysis/{audit_id}/upload-result
        -> Accept raw text output from user's AI tool
        -> Parse findings (LLM-assisted extraction of structured data)
        -> Store in code_analysis_results table
        -> Trigger re-scoring with enriched data
        -> Generate deeper, code-specific recommendations
```

**Key Decision: No direct GitHub/GitLab integration in v2.** This avoids OAuth complexity, repo permission management, and security concerns. Users paste output manually. V3 can add a GitHub App.

### 8. Jira CSV Export

**Architecture: Server-side CSV generation with customizable columns**

```
Data Flow:
  User clicks "Export to Jira" on recommendations page
    -> GET /api/v1/recommendations/{audit_id}/export/jira-csv
      -> Query parameters: grouping (by_page, by_category, by_priority), epic_link, fields
      -> Load AuditRecommendation records
      -> Map to Jira CSV columns:
        - Summary: criterion_name + page_url
        - Description: summary + action_steps + code_snippet
        - Issue Type: "Story" or "Task"
        - Priority: map high->Highest, medium->High, low->Medium
        - Labels: category, "geo-audit", domain
        - Epic Link: user-provided epic key
        - Story Points: based on complexity heuristic
      -> Generate CSV using csv module (not pandas -- lighter dependency)
      -> Return as StreamingResponse with Content-Disposition header
```

**Column mapping is configurable** because different Jira instances have different custom fields. Provide sensible defaults but let users override column names in the request.

### 9. Production Dashboard

**Architecture: Real data from DB, Nuxt 3 composables, Chart.js**

```
Data Flow:
  Dashboard page loads
    -> GET /api/v1/dashboard/stats (overview numbers)
      -> Total audits, average scores, trend direction
    -> GET /api/v1/dashboard/history (score over time)
      -> Audit scores with timestamps for trend chart
    -> GET /api/v1/dashboard/recent (latest audits)
      -> Last 5 audits with status and scores

  Brand-specific dashboard:
    -> GET /api/v1/brands/{brand_id}/dashboard
      -> All audits for this brand, score progression
      -> Competitor positioning over time
      -> Recommendation progress (done/open/dismissed)
```

---

## Patterns to Follow

### Pattern 1: Celery Task for Long Operations

**What:** Any operation taking >2 seconds should be a Celery background task.
**When:** Audit pipeline, PDF generation, competitor crawling, code analysis parsing.
**Why:** Prevents FastAPI thread starvation. The existing audit pipeline already follows this pattern.

```python
@celery_app.task(bind=True, name="app.tasks.reports.generate_report")
def generate_report(self, audit_id: str, format: str):
    db = SessionLocal()
    try:
        # Load data, render template, generate PDF
        ...
    finally:
        db.close()
```

### Pattern 2: Dependency Injection for Feature Gating

**What:** Use FastAPI `Depends()` for subscription tier checking.
**When:** Any endpoint that varies by tier (report download, chat, competitor crawl).
**Why:** Clean separation of auth/billing logic from business logic.

```python
@router.get("/reports/{audit_id}/download")
async def download_report(
    audit_id: str,
    tier: SubscriptionTier = Depends(require_tier(SubscriptionTier.PRO)),
    db: Session = Depends(get_db),
    current_user: Profile = Depends(get_current_active_user),
):
    ...
```

### Pattern 3: Audit Ownership Verification

**What:** Every endpoint that accesses audit data verifies ownership.
**When:** All audit-related endpoints (already implemented consistently).
**Why:** Multi-tenant security -- users must only see their own data.

The existing `_verify_audit_ownership()` pattern should be extracted into a shared dependency:

```python
# app/core/dependencies.py
def get_user_audit(audit_id: str, db: Session, current_user: Profile) -> Audit:
    audit = db.query(Audit).filter(Audit.id == audit_id).first()
    if not audit or audit.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Audit not found")
    return audit
```

### Pattern 4: Context-Aware LLM Calls

**What:** Inject structured audit context into LLM system prompts for chat.
**When:** Chat assistant, future AI-enhanced recommendations.
**Why:** Focused, accurate responses grounded in actual audit data.

```python
def build_chat_context(audit: Audit, db: Session) -> str:
    """Build a summarized context string from audit data."""
    scores = f"Optimization: {audit.optimization_score}/100"
    # Load top 5 failing criteria
    failing = db.query(CriterionResult).filter(...).order_by(CriterionResult.score.asc()).limit(5).all()
    # Load top 3 recommendations
    recs = db.query(AuditRecommendation).filter(...).limit(3).all()
    # Build context template
    return f"""You are an SEO/GEO expert analyzing {audit.domain}.
Audit scores: {scores}
Top issues: {format_criteria(failing)}
Top recommendations: {format_recs(recs)}
Answer questions about this audit. Be specific and actionable."""
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: LLM for Deterministic Logic

**What:** Using LLM calls to generate recommendations or compute scores.
**Why bad:** Non-reproducible results, API costs per audit, latency, hallucination risk.
**Instead:** The existing deterministic RecommendationEngine is correct. Keep scoring and recommendations rule-based. Use LLMs only for chat (user-initiated, interactive) and code analysis output parsing.

### Anti-Pattern 2: Synchronous Heavy Operations in API Handlers

**What:** Running crawler, scorer, or PDF generator inside a FastAPI endpoint handler.
**Why bad:** Blocks API threads, causes timeouts, poor UX.
**Instead:** Use Celery tasks. Return 202 Accepted with a task ID, let frontend poll for completion. The existing audit pipeline already follows this correctly.

### Anti-Pattern 3: Fat Celery Tasks

**What:** A single massive Celery task (like the current `run_crawl_and_generate`) that does everything.
**Why bad:** If one stage fails, the entire task fails. No partial results. Hard to test stages independently. Currently at ~350 lines.
**Instead:** Consider breaking into Celery chain/group primitives for independent stages:

```python
# Future refactor (not urgent, but recommended):
from celery import chain, group

audit_pipeline = chain(
    crawl_url.s(audit_id, url),
    generate_queries.s(),
    dispatch_to_engines.s(),
    analyze_mentions.s(),
    score_pages.s(),
    group(
        discover_competitors.s(),
        generate_recommendations.s(),
    ),
    mark_completed.s(),
)
```

**Mitigation for now:** The current monolithic task works because each stage is wrapped in try/except with non-fatal failures for later stages. This is acceptable for v2 but should be refactored when adding task chaining.

### Anti-Pattern 4: N+1 Queries

**What:** Loading related records in loops instead of using eager loading.
**Why bad:** Performance degrades as data grows.
**Instead:** The existing `get_audit` endpoint correctly uses `joinedload()`. Follow this pattern everywhere.

### Anti-Pattern 5: Storing Secrets in Code

**What:** Hardcoded Stripe price IDs, API keys, or webhook secrets.
**Why bad:** Security risk, environment inflexibility.
**Instead:** All configuration through pydantic-settings `.env` loading (already established pattern). Stripe price IDs should be in settings, not hardcoded in endpoint handlers.

---

## Integration Points Between Components

### Dependency Graph

```
ScoringPipeline (Phase 1)
    |
    +---> RecommendationEngine (Phase 2) ---> JiraCSVExport (Phase 3)
    |                                    \--> ReportGenerator (Phase 3)
    |                                    \--> ChatAssistant (Phase 4)
    |
    +---> CompetitorBenchmarking (Phase 2)
    |         |
    |         +---> RecommendationEngine (competitor averages)
    |
    +---> CodeAnalysisFlow (Phase 4, prompt generation uses scoring gaps)
    |
    +---> ProductionDashboard (Phase 5, displays all scores)

PaymentGating (Phase 3) -- independent, gates access to:
    -> ReportGenerator
    -> ChatAssistant
    -> CompetitorBenchmarking (number of competitors)
    -> CodeAnalysisFlow
    -> JiraCSVExport
```

### Build Order (strict dependency chain)

1. **ScoringPipeline** -- Everything depends on real scores. Without real criterion results, recommendations are meaningless, reports show zeros, chat has nothing to discuss, and the dashboard displays fake data. This is the absolute first priority.

2. **RecommendationEngine enhancements + CompetitorBenchmarking** -- Once scoring works, recommendations automatically produce better output. Competitor benchmarking adds the "competitor_avg" comparison data that recommendations use for gap_score calculation.

3. **PaymentGating + ReportGenerator + JiraCSVExport** -- These are "output" features that consume completed audit data. Payment gating is independent but needed before public launch. Reports and Jira export are high-value features that convert free users to paid.

4. **ChatAssistant + CodeAnalysisFlow** -- These are "interactive" features. Chat requires working scores and recommendations to be useful. Code analysis prompts are generated from audit gaps.

5. **ProductionDashboard** -- Requires all other components to produce real data. Building the dashboard last ensures every metric displayed is genuine.

---

## Scalability Considerations

| Concern | At 100 users | At 10K users | At 1M users |
|---------|--------------|--------------|-------------|
| **Audit throughput** | Single Celery worker sufficient | 3-5 workers with queue routing | Distributed workers, message priority |
| **DB connections** | Supabase free tier (60 connections) | Supabase Pro (connection pooling) | Read replicas, connection pooling (PgBouncer) |
| **AI API costs** | ~$10/day at $0.10/audit | ~$1000/day, need caching + cheaper models | Negotiated enterprise API rates, aggressive caching |
| **PDF generation** | In-process WeasyPrint | Dedicated Celery queue for reports | Serverless PDF service (Lambda/Cloud Run) |
| **Chat WebSockets** | FastAPI handles ~100 concurrent easily | Need WebSocket connection management | Redis Pub/Sub for multi-instance WebSocket |
| **Redis** | Single instance (6379) | Redis cluster or managed Redis | Redis Sentinel with read replicas |
| **Storage (reports)** | Local filesystem or Supabase Storage | Supabase Storage / S3 | CDN-fronted S3 with lifecycle policies |

### Near-term Scaling Actions (before 1K users)

1. **Queue routing:** Separate Celery queues for audit tasks vs. report generation vs. competitor crawling. Prevents long-running competitor crawls from blocking quick audit dispatches.

```python
# celery_app.py
celery_app.conf.task_routes = {
    "app.tasks.audit_tasks.*": {"queue": "audit"},
    "app.tasks.reports.*": {"queue": "reports"},
    "app.tasks.competitors.*": {"queue": "competitors"},
}
```

2. **Connection pooling:** Add SQLAlchemy `pool_size` and `max_overflow` configuration. The current `create_engine()` call should explicitly set these.

3. **Redis caching TTLs:** Current 24h TTL for crawl data is appropriate. Add 7-day TTL for AI responses (already noted in critique). Add 30-day TTL for generated report PDFs.

---

## Suggested Build Order (for Roadmap)

| Order | Component | Rationale | Estimated Complexity |
|-------|-----------|-----------|---------------------|
| 1 | ScoringPipeline (all 61 criteria) | Everything depends on it. No value without real scores. | HIGH (most effort) |
| 2 | RecommendationEngine + CompetitorBenchmarking | Immediate value once scoring works. Already has framework. | MEDIUM |
| 3 | PaymentGating (Stripe) | Must work before public launch. Independent of other features. | MEDIUM |
| 4 | ReportGenerator (PDF/HTML) | High perceived value. Converts free -> paid. | MEDIUM |
| 5 | JiraCSVExport | Small effort, high value for agency users. | LOW |
| 6 | ChatAssistant (WebSocket) | Differentiatior. Requires working audit data. | MEDIUM-HIGH |
| 7 | CodeAnalysisFlow | Unique differentiator. Requires audit data + user interaction. | MEDIUM |
| 8 | ProductionDashboard | Displays all the real data from previous phases. | MEDIUM |

---

## Sources

- Existing codebase audit: `/home/salim/Informatique/Perso/Endexa/geo-platform-mvp/backend/app/` (HIGH confidence -- direct code reading)
- Comprehensive critique: `endexa-audit-review-2/ENDEXA-COMPREHENSIVE-CRITIQUE.md` (HIGH confidence -- authored with full code access)
- [FastAPI + Celery production guide](https://medium.com/@dewasheesh.rana/celery-redis-fastapi-the-ultimate-2025-production-guide-broker-vs-backend-explained-5b84ef508fa7) (MEDIUM confidence)
- [FastAPI + Celery task chaining patterns](https://gist.github.com/coderberry/e13165e2ae66ecbf3df9ee1aa0ffb373) (MEDIUM confidence)
- [FastAPI WebSocket + LLM streaming](https://dev.to/dpills/create-a-streaming-ai-assistant-with-chatgpt-fastapi-websockets-and-react-3ehf) (MEDIUM confidence)
- [WeasyPrint PDF generation with FastAPI](https://medium.com/@pariosur/weasyprint-generating-dynamic-pdf-reports-with-python-37b3d9e58e16) (MEDIUM confidence)
- [FastAPI + Stripe integration patterns](https://www.fast-saas.com/blog/fastapi-stripe-integration/) (MEDIUM confidence)
- [Jira CSV export patterns](https://community.atlassian.com/forums/App-Central-articles/Jira-Export-6-Tips-to-Jira-Export-to-Excel-CSV-PDF-and-More/ba-p/2814825) (MEDIUM confidence)
