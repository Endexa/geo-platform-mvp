# Phase 8: Actionable Recommendations - Research

**Researched:** 2026-02-22
**Domain:** Recommendation engine, gap analysis, sentiment analysis, content gap identification, Markdown export
**Confidence:** HIGH (codebase patterns well-established; LiteLLM JSON mode verified; sentiment approach verified)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Recommendation detail level**
- Two tiers: actionable guidance as default view + step-by-step with code snippets expandable per recommendation
- Example default: "Add FAQPage schema to your pricing page -- competitors have it, 3.2x citation rate (BrightEdge)"
- Example expanded: Full JSON-LD code snippet, placement instructions, validation steps
- Data structure must be export-friendly for Phase 9 PDF/CSV consumption

**Recommendation tracking**
- Recommendations have a done/dismissed state with progress tracking
- Progress bar: "12/28 recommendations addressed"
- State persists across re-audits -- when a recommendation is re-generated, previous done/dismissed status carries over if the recommendation matches

**Exportable fix plans**
- Recommendations exportable as machine-readable plan files (Markdown format) that users can feed directly into a Claude Code / AI coding session to auto-fix their site
- Two export scopes available: per-page plan file and combined full-site plan file
- Format inspired by GSD PLAN.md structure -- clear tasks, file paths, code changes, acceptance criteria

**Negative sentiment handling**
- Negative AI mentions get flagged with exact quote + a specific recommendation to address the issue
- Example: "ChatGPT says 'Stripe's pricing is confusing' -- improve pricing page clarity with comparison table and FAQ"

**Sentiment per engine**
- Sentiment breakdown shown per-engine: "ChatGPT: mostly positive, Perplexity: mixed, Claude: not mentioned"
- Users can see which engines have issues and prioritize fixes per engine

**Content gap presentation**
- Content gaps displayed as topic cards -- visual and scannable
- Each card: topic name, which competitors get mentioned, user's coverage status, action needed
- Each gap includes a mini content brief: suggested title, 3-5 key points to cover, target keywords from AI queries

### Claude's Discretion
- Recommendation organization (priority-first, page-first, or category-first -- or combination with tabs/filters)
- Navigation pattern between scoring page and recommendations (inline links, separate page, or both)
- Evidence display format (inline stats vs expandable detail)
- Competitor URL linking in content gap cards (show competitor pages or not)
- Sentiment classification granularity (3-way vs 5-level)
- Sentiment implementation method (LLM-based vs rule-based vs hybrid)
- Content brief generation method (LLM-generated vs template-based)
- Content recommendation depth (topic + rationale vs full content brief -- user prefers briefs when possible)

### Deferred Ideas (OUT OF SCOPE)
- PDF/CSV export of recommendations -- Phase 9 (Dashboard & Reporting)
- Recommendation trend tracking over time (how recommendations change between audits) -- Phase 9
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| REC-01 | App generates page-specific recommendations by comparing user site scores against competitor scores and research-backed best practices | Gap analysis engine reads CriterionResult records per page, compares against CompetitorAudit category averages; research benchmarks are hard-coded constants in the service |
| REC-02 | Each recommendation includes evidence: research-backed impact data, specific competitor comparison, exact gap identified | Each GapRecommendation dataclass carries evidence_stat, competitor_gap, and criterion_gap fields; serialized into AuditRecommendation JSONB |
| REC-03 | Recommendations are prioritized by estimated impact (High/Medium/Low) based on research data | Impact thresholds: High >25% citation improvement (schema 2.3-2.5x, answer-first +40%), Medium 10-25% (FAQ +28%, freshness 3.2x), Low <10% |
| REC-04 | App classifies sentiment of AI mentions (positive, negative, neutral) and surfaces sentiment patterns per engine | LiteLLM call per mention context_quote using gemini/gemini-2.5-flash for cost efficiency; results stored in new MentionSentiment table; per-engine aggregation at query time |
| REC-05 | App identifies content gaps: topics where competitors are mentioned but user is not, linked to specific pages the user could create or improve | Cross-reference AuditQuery set against DiscoveredCompetitor.queries_mentioned_in; queries where competitor mention_count > 0 and user visibility = 0 become gap topics |
</phase_requirements>

---

## Summary

Phase 8 builds the recommendation engine on top of the scoring and competitor data produced in Phases 6 and 7. The core algorithm is deterministic gap analysis: for each user page and each criterion, compare the user's score against (a) competitor category averages from `CompetitorAudit` records and (b) hard-coded research benchmarks. Low scores on high-impact criteria become recommendations, enriched with specific evidence strings, competitor comparison facts, and priority classification. This is the most architectural value-add of the phase -- the logic must run synchronously at audit completion (not on-demand) and store results in a new `AuditRecommendation` model that supersedes the old legacy `Recommendation` model.

Sentiment analysis (REC-04) classifies each existing `BrandMention.context_quote` into positive/negative/neutral using a LiteLLM call (gemini-2.5-flash, JSON mode). A batch job runs once per audit over all mentions. Results go into a new `MentionSentiment` table. Per-engine sentiment patterns are computed at query time by aggregating over the sentiments for all mentions belonging to engine responses for a given engine. This avoids expensive re-computation and keeps storage costs low.

Content gap identification (REC-05) is deterministic and query-based: cross-reference which `AuditQuery` topics produced zero user brand mentions but non-zero competitor entity mentions. Those queries become "gap topics". A lightweight LLM call (or template) then generates a mini brief per gap. The frontend displays gaps as scannable topic cards with a mini brief inside each one.

**Primary recommendation:** Build RecommendationEngine as a pure Python service (no async required, runs in Celery synchronously) that reads from existing DB tables and writes to new `AuditRecommendation` and `MentionSentiment` tables. Do NOT use the legacy `Recommendation` model -- replace it in the API layer with the new audit-scoped model.

---

## Standard Stack

### Core (all already installed -- no new pip packages required)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| litellm | installed | LLM calls for sentiment + content briefs | Already used in dispatch_service, query_generator; api_key pattern documented |
| sqlalchemy | installed | ORM for new models | Already used everywhere |
| pydantic | v2 installed | Response schemas, structured output | Already used everywhere |
| loguru | installed | Logging | Already used everywhere |

### New Models Required

Two new SQLAlchemy models are needed. The old `Recommendation` model (tied to `Analysis`, not `Audit`) remains for backward compat but is NOT used in Phase 8.

**`AuditRecommendation`** -- replaces Recommendation for audit-scoped recommendations:
```python
# backend/app/models/audit_recommendation.py
class AuditRecommendation(Base):
    __tablename__ = "audit_recommendations"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    audit_id = Column(UUID, ForeignKey("audits.id"), nullable=False, index=True)
    page_url = Column(String, nullable=True)           # None = site-wide
    criterion_id = Column(String, nullable=False)      # e.g. "SD7"
    criterion_name = Column(String, nullable=False)
    category = Column(String, nullable=False)          # crawlability/content_structure/structured_data/authority
    priority = Column(String, nullable=False)          # "high", "medium", "low"
    impact_label = Column(String, nullable=False)      # e.g. "3.2x citation rate"
    impact_pct = Column(Integer, nullable=True)        # e.g. 320 means 3.2x (store as int * 100)
    user_score = Column(Integer, nullable=False)       # 0-100
    competitor_avg = Column(Integer, nullable=True)    # from CompetitorAudit, None if no competitor data
    gap_score = Column(Integer, nullable=False)        # competitor_avg - user_score (or benchmark - user_score)
    summary = Column(Text, nullable=False)             # "Add FAQPage schema -- competitors have it, 3.2x citation rate"
    action_steps = Column(JSONB, nullable=False)       # list of strings (default view + expanded steps)
    code_snippet = Column(Text, nullable=True)         # JSON-LD, robots.txt, etc. for the expanded view
    evidence_source = Column(String, nullable=False)   # "BrightEdge 2024", "Princeton GEO paper"
    recommendation_hash = Column(String, nullable=False, index=True)  # SHA-256(audit_id+criterion_id+page_url) for tracking carry-over
    status = Column(String, nullable=False, default="open")  # "open", "done", "dismissed"
    created_at = Column(DateTime, default=...)
    updated_at = Column(DateTime, default=..., onupdate=...)
```

**`MentionSentiment`** -- per-mention sentiment classification:
```python
# backend/app/models/mention_sentiment.py
class MentionSentiment(Base):
    __tablename__ = "mention_sentiments"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    audit_id = Column(UUID, ForeignKey("audits.id"), nullable=False, index=True)
    brand_mention_id = Column(UUID, ForeignKey("brand_mentions.id"), nullable=False, unique=True)
    engine = Column(String, nullable=False)            # "openai", "anthropic", "perplexity", "gemini"
    sentiment = Column(String, nullable=False)         # "positive", "negative", "neutral"
    confidence = Column(Integer, nullable=False)       # 0-100
    context_quote = Column(Text, nullable=False)       # copied from BrandMention for convenience
    created_at = Column(DateTime, default=...)
```

### Installation

No new packages needed. Everything is already in `requirements.txt`.

---

## Architecture Patterns

### Recommended Project Structure (additions only)

```
backend/app/
├── models/
│   ├── audit_recommendation.py   # NEW - replaces old Recommendation for audit flow
│   └── mention_sentiment.py      # NEW - per-mention sentiment
├── services/
│   ├── recommendation_engine.py  # NEW - gap analysis + priority classification
│   └── sentiment_service.py      # NEW - LLM-based sentiment classification
├── api/
│   └── recommendations.py        # NEW - CRUD + Markdown export endpoints

frontend/
├── pages/
│   └── recommendations.vue       # NEW - full recommendations page
├── components/
│   ├── RecommendationCard.vue    # NEW - single recommendation with expand/collapse
│   ├── RecommendationProgress.vue # NEW - "12/28 addressed" progress bar
│   ├── SentimentBreakdown.vue    # NEW - per-engine sentiment summary
│   └── ContentGapCard.vue        # NEW - topic card with mini brief
```

### Pattern 1: Gap Analysis Engine (Deterministic, No LLM)

**What:** Compare per-criterion user scores from `CriterionResult` records against competitor category averages from `CompetitorAudit` records and hard-coded research benchmarks. Produce ranked recommendations.

**When to use:** Runs once at end of audit (appended to Celery task pipeline, Stage 8).

**Key data flow:**
```
CriterionResult (per page, per criterion)
  + CompetitorAudit (category averages per competitor)
  + RESEARCH_BENCHMARKS dict (hard-coded impact stats)
  → GapRecommendation list
  → sorted by gap_score * impact_weight
  → stored as AuditRecommendation records
```

**Research benchmarks constant (in recommendation_engine.py):**
```python
# Source: Princeton GEO paper, BrightEdge, Surfer SEO, Frase.io, Ahrefs 75K study
CRITERION_RESEARCH_MAP: dict[str, dict] = {
    "SD7": {  # FAQPage schema
        "impact_pct": 320,           # 3.2x = +220% over baseline, stored as 320
        "impact_label": "3.2x citation rate",
        "evidence_source": "BrightEdge + Frase.io",
        "priority_base": "high",
    },
    "SD1": {  # JSON-LD presence
        "impact_pct": 240,           # 2.3-2.5x in AI Overviews
        "impact_label": "2.3-2.5x more likely in AI Overviews",
        "evidence_source": "BrightEdge",
        "priority_base": "high",
    },
    "CS1": {  # Answer-first format
        "impact_pct": 140,           # +40% citations
        "impact_label": "+40% citations",
        "evidence_source": "Princeton GEO paper",
        "priority_base": "high",
    },
    "CS4": {  # Statistics in content
        "impact_pct": 140,           # +40% visibility
        "impact_label": "+40% visibility boost",
        "evidence_source": "Princeton GEO paper",
        "priority_base": "high",
    },
    "CS8": {  # Data tables
        "impact_pct": 410,           # 4.1x citations
        "impact_label": "4.1x more AI citations",
        "evidence_source": "Surfer SEO 46M analysis",
        "priority_base": "high",
    },
    "CS5": {  # Quotations from authorities
        "impact_pct": 120,           # +15-25%, use midpoint 20%
        "impact_label": "+15-25% citation boost",
        "evidence_source": "Princeton GEO paper",
        "priority_base": "medium",
    },
    "SD5": {  # Content freshness (<30 days)
        "impact_pct": 320,           # 3.2x more citations
        "impact_label": "3.2x more citations (fresh content)",
        "evidence_source": "Industry benchmark",
        "priority_base": "medium",
    },
    # Add remaining criteria with default impact_pct=110 / priority_base="low"
}
```

**Priority classification:**
- HIGH = impact_pct >= 200 AND gap_score >= 30 (or any criterion with gap_score >= 50)
- MEDIUM = impact_pct >= 120 AND gap_score >= 20
- LOW = everything else with gap_score >= 10
- Skip criteria where gap_score < 10 (already close enough)

### Pattern 2: Recommendation Hash for Cross-Audit Tracking

**What:** Each `AuditRecommendation` gets a stable `recommendation_hash` computed from `(criterion_id, page_url_normalized)`. When the recommendation engine runs for a re-audit, it looks up hashes from previous audits to carry over done/dismissed status.

**Why hashing:** User can run multiple audits over time. The hash uniquely identifies "this type of fix for this page" regardless of audit ID.

**Implementation:**
```python
import hashlib

def _compute_rec_hash(criterion_id: str, page_url: str) -> str:
    """Stable hash for recommendation identity across re-audits."""
    # Normalize URL: strip trailing slash, lowercase scheme+host, keep path
    from urllib.parse import urlparse
    parsed = urlparse(page_url.lower())
    normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"
    key = f"{criterion_id}|{normalized}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]  # 16 chars sufficient
```

**Carry-over logic (when generating recommendations for a new audit):**
```python
# Look up previous status for this hash, for this user
prev_status = (
    db.query(AuditRecommendation.status)
    .join(Audit, AuditRecommendation.audit_id == Audit.id)
    .filter(Audit.user_id == current_user_id)
    .filter(AuditRecommendation.recommendation_hash == rec_hash)
    .filter(AuditRecommendation.status.in_(["done", "dismissed"]))
    .order_by(AuditRecommendation.created_at.desc())
    .first()
)
initial_status = prev_status[0] if prev_status else "open"
```

### Pattern 3: Sentiment Analysis (LLM-Based, Batch)

**What:** For each `BrandMention` with a `context_quote`, call LiteLLM with a structured JSON prompt to classify as positive/negative/neutral. Batch all mentions for an audit in a single service call (one LLM call per mention, concurrent with a limit).

**Why LLM-based over rule-based:** Context matters. "Stripe charges the most but offers the best reliability" is positive. "Stripe is mentioned" is neutral. VADER/TextBlob would misclassify these. LLM zero-shot at 3-class gets ~92% accuracy (GPT-4 benchmark). Using gemini-2.5-flash keeps cost minimal.

**Cost estimate:** ~200 chars per context_quote, 107 mentions from Stripe audit example. Each call: ~100 input tokens + 10 output tokens. At Gemini 2.5 Flash pricing (~$0.00015/1K tokens), 107 calls = ~$0.002 total. Acceptable.

**Implementation pattern:**
```python
# Source: LiteLLM docs - https://docs.litellm.ai/docs/completion/json_mode
import litellm
from app.core.config import settings

def classify_sentiment(context_quote: str) -> dict:
    """Classify brand mention sentiment using LiteLLM JSON mode."""
    response = litellm.completion(
        model="gemini/gemini-2.5-flash",
        api_key=settings.GEMINI_API_KEY,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "You classify brand mentions as positive, negative, or neutral. "
                    "Return JSON: {\"sentiment\": \"positive\"|\"negative\"|\"neutral\", \"confidence\": 0-100, \"reason\": \"brief\"}"
                ),
            },
            {
                "role": "user",
                "content": f"Classify the sentiment of this brand mention:\n\n\"{context_quote}\"",
            },
        ],
        temperature=0.0,
    )
    import json
    return json.loads(response.choices[0].message.content)
```

**CRITICAL - API key pattern:** Follow established pattern from `dispatch_service.py` and `query_generator.py`. pydantic-settings loads `.env` into Settings but NOT into `os.environ`. Always pass `api_key=settings.GEMINI_API_KEY` explicitly to `litellm.completion()`. Never rely on env var auto-detection.

**Batch processing (synchronous for Celery):**
```python
def analyze_audit_sentiments(self, audit_id: str) -> list[MentionSentiment]:
    """Classify sentiments for all brand mentions in an audit."""
    # Load all mentions with their engine context
    mentions_with_engine = (
        self.db.query(BrandMention, EngineResponse.engine)
        .join(EngineResponse, BrandMention.engine_response_id == EngineResponse.id)
        .join(AuditQuery, EngineResponse.audit_query_id == AuditQuery.id)
        .filter(AuditQuery.audit_id == audit_id)
        .all()
    )

    results = []
    for mention, engine in mentions_with_engine:
        try:
            classification = self.classify_sentiment(mention.context_quote)
            sentiment_record = MentionSentiment(
                audit_id=audit_id,
                brand_mention_id=mention.id,
                engine=engine,
                sentiment=classification["sentiment"],
                confidence=classification.get("confidence", 80),
                context_quote=mention.context_quote,
            )
            self.db.add(sentiment_record)
            results.append(sentiment_record)
        except Exception as e:
            logger.warning("Sentiment classification failed for mention {}: {}", mention.id, e)
    self.db.flush()
    return results
```

### Pattern 4: Content Gap Identification (Deterministic)

**What:** Cross-reference `AuditQuery` set against `DiscoveredCompetitor.queries_mentioned_in` to find queries where competitors appear but the user does not.

**Data sources:**
- `DiscoveredCompetitor.queries_mentioned_in` = JSONB list of `AuditQuery.id` strings where this entity appeared
- `BrandMention` records = where the user brand appeared (by `engine_response_id` -> `AuditQuery.id`)
- Gap = queries_where_competitor_appears MINUS queries_where_user_appears

**Algorithm:**
```python
def identify_content_gaps(self, audit_id: str) -> list[ContentGap]:
    """Find topics where competitors appear in AI responses but the user brand does not."""
    # 1. All queries for this audit
    all_queries = {str(q.id): q.query_text for q in
                   self.db.query(AuditQuery).filter(AuditQuery.audit_id == audit_id).all()}

    # 2. Queries where the user brand was mentioned
    user_mentioned_query_ids = set(
        str(r.AuditQuery.id)
        for r in self.db.query(BrandMention, EngineResponse, AuditQuery)
        .join(EngineResponse, BrandMention.engine_response_id == EngineResponse.id)
        .join(AuditQuery, EngineResponse.audit_query_id == AuditQuery.id)
        .filter(AuditQuery.audit_id == audit_id)
        .all()
    )

    # 3. Per-query: which competitors appear?
    competitors = (
        self.db.query(DiscoveredCompetitor)
        .filter(DiscoveredCompetitor.audit_id == audit_id)
        .filter(DiscoveredCompetitor.is_user_brand.is_(False))
        .all()
    )

    # Build query_id -> [competitor_names] index
    query_to_competitors: dict[str, list[str]] = {}
    for comp in competitors:
        for qid in (comp.queries_mentioned_in or []):
            query_to_competitors.setdefault(str(qid), []).append(comp.entity_name)

    # 4. Gap = queries where >=1 competitor mentioned and user not mentioned
    gaps = []
    for query_id, query_text in all_queries.items():
        if query_id not in user_mentioned_query_ids and query_id in query_to_competitors:
            gaps.append(ContentGap(
                query_id=query_id,
                query_text=query_text,
                competitors_mentioned=query_to_competitors[query_id],
                suggested_title=None,  # LLM or template fills this
                key_points=[],
            ))
    return gaps
```

**Content brief generation (Claude's Discretion - recommend template-based with LLM enrichment):** For each gap, generate a brief using a template first (fast, free). Optionally enrich with a single LiteLLM call if `GEMINI_API_KEY` is set. This keeps cost at $0 minimum, $0.001/gap maximum.

Template approach (no LLM):
```python
def _template_brief(gap: ContentGap) -> ContentBrief:
    return ContentBrief(
        suggested_title=f"Complete Guide: {gap.query_text.capitalize()}",
        key_points=[
            f"Answer the question: {gap.query_text}",
            "Include statistics and data to support claims",
            "Add FAQPage schema with the most common questions",
            "Cite authoritative sources for E-E-A-T signals",
            f"Compare your offering to {', '.join(gap.competitors_mentioned[:2])}",
        ],
        target_queries=[gap.query_text],
    )
```

### Pattern 5: Markdown Fix Plan Export

**What:** Endpoint that generates a structured Markdown plan file from an audit's recommendations, suitable for feeding into Claude Code or other AI coding assistants.

**Format (GSD-inspired):**
```markdown
# GEO Fix Plan: {domain} - {date}

## Summary
{N} high-priority fixes | {M} medium | {K} low
Addressing these fixes is estimated to improve your AI citation rate by up to {max_impact}%.

## High Priority Fixes

### Fix 1: Add FAQPage Schema to /pricing
**Evidence:** FAQPage schema gives 3.2x citation rate (BrightEdge + Frase.io)
**Your score:** 0/100 | **Competitor avg:** 85/100 | **Gap:** 85 points
**Status:** Open

**Steps:**
1. Add the following JSON-LD to the `<head>` of `/pricing`:
```json
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [...]
}
```
2. Validate at https://validator.schema.org/
3. Deploy and re-run audit to verify.

**Acceptance criteria:**
- [ ] JSON-LD block present in page source
- [ ] Schema validator shows no errors
- [ ] Audit re-run shows SD7 score > 80

---
```

**Export scope:** Two endpoints:
- `GET /api/v1/recommendations/{audit_id}/export/markdown?page_url=...` (single page)
- `GET /api/v1/recommendations/{audit_id}/export/markdown` (full site, all pages)

Response: `Content-Type: text/markdown` with `Content-Disposition: attachment; filename=fix-plan-{domain}.md`

### Pattern 6: Frontend Recommendation Architecture

**Recommendation:** Use tabs for organization (matches existing pattern on audit page). Priority tab first (High/Medium/Low), with a "By Page" secondary tab.

**Recommendation card structure (two-tier):**
```
+-------------------------------------------------------+
| [H] FAQPage Schema -- /pricing                  [Done][Dismiss] |
| "Add FAQPage schema -- competitors have it, 3.2x citation rate" |
| Impact: HIGH  Gap: 85pts  Competitor avg: 85                   |
|                                          [See Steps v]          |
+-------------------------------------------------------+
  (expanded):
  Steps: 1. Add JSON-LD... 2. Validate... 3. Re-audit
  Code: <pre>{ "@context": ... }</pre>
  Source: BrightEdge + Frase.io (2024)
```

**Progress tracking component:**
```vue
<!-- RecommendationProgress.vue -->
<div class="flex items-center space-x-4">
  <div class="flex-1 bg-gray-200 rounded-full h-2">
    <div class="bg-green-500 h-2 rounded-full transition-all duration-300"
         :style="{ width: `${progress}%` }" />
  </div>
  <span class="text-sm text-gray-600">{{ done }}/{{ total }} addressed</span>
</div>
```

**Expand/collapse pattern (Vue 3, no library needed):**
```vue
<div v-show="expanded"
     class="overflow-hidden transition-all duration-200">
  <!-- expanded content -->
</div>
<button @click="expanded = !expanded"
        class="text-sm text-primary-600 cursor-pointer focus-visible:ring-2 focus-visible:ring-primary-500">
  {{ expanded ? 'Hide Steps' : 'See Steps' }}
</button>
```

**Sentiment breakdown component:**
```vue
<!-- SentimentBreakdown.vue: one row per engine -->
<div class="grid grid-cols-2 gap-2">
  <div v-for="engine in engines" :key="engine.name"
       class="flex items-center justify-between p-2 bg-gray-50 rounded">
    <span class="text-sm font-medium">{{ engine.label }}</span>
    <span :class="sentimentColor(engine.dominant)" class="text-xs font-semibold px-2 py-1 rounded">
      {{ engine.dominant }}
    </span>
  </div>
</div>
```

**Content gap card:**
```vue
<!-- ContentGapCard.vue -->
<div class="border border-amber-200 bg-amber-50 rounded-lg p-4">
  <div class="flex items-start justify-between">
    <h4 class="text-sm font-semibold text-gray-900">{{ gap.query_text }}</h4>
    <span class="text-xs text-amber-700 font-medium">Missing</span>
  </div>
  <p class="text-xs text-gray-500 mt-1">
    Mentioned: {{ gap.competitors_mentioned.join(', ') }}
  </p>
  <div v-if="showBrief" class="mt-3 border-t border-amber-200 pt-3">
    <p class="text-xs font-semibold text-gray-700">Suggested: {{ gap.brief.title }}</p>
    <ul class="mt-1 space-y-1">
      <li v-for="point in gap.brief.key_points" :key="point"
          class="text-xs text-gray-600">- {{ point }}</li>
    </ul>
  </div>
</div>
```

### Pattern 7: Celery Pipeline Integration

Phase 8 adds Stage 8 (RECOMMENDING) to the existing audit pipeline. It runs after Stage 7 (DISCOVERING_COMPETITORS).

**New AuditStatus enum value:**
```python
RECOMMENDING = "recommending"
```

**audit_tasks.py Stage 8 (appended after Stage 7):**
```python
# Stage 8: Generate recommendations and sentiment
audit.status = AuditStatus.RECOMMENDING.value
db.commit()

from app.services.recommendation_engine import RecommendationEngine
rec_engine = RecommendationEngine(db)
recs = rec_engine.generate_recommendations(
    audit_id=audit_id,
    user_id=str(audit.user_id),
)

from app.services.sentiment_service import SentimentService
sentiment_svc = SentimentService(db)
sentiments = sentiment_svc.analyze_audit_sentiments(audit_id=audit_id)
gaps = rec_engine.identify_content_gaps(audit_id=audit_id)
rec_engine.save_content_gaps(audit_id=audit_id, gaps=gaps)

db.commit()
logger.info("Audit {}: generated {} recommendations, {} sentiments, {} content gaps",
            audit_id, len(recs), len(sentiments), len(gaps))
```

**ContentGap storage:** Add a `content_gaps` JSONB column to `Audit` model OR create a `ContentGap` table. Recommend JSONB on `Audit` to avoid another migration table for a relatively small, non-queryable payload.

### Anti-Patterns to Avoid

- **Using the old `Recommendation` model:** It's tied to `Analysis` (legacy), not `Audit`. Phase 8 uses `AuditRecommendation` tied to `Audit`. The old model stays but is not extended.
- **Running sentiment analysis synchronously per mention on request:** Batch it once at audit completion. Storing results avoids re-running LLM calls on every page load.
- **Generating recommendations on-demand (when user opens the page):** Run at audit completion in Celery. Recommendations must be ready when the page loads -- no lazy generation.
- **Computing per-engine sentiment aggregation in Python loops at query time (N+1):** Use a single aggregating SQL query or subquery, not Python loops over all mentions.
- **Storing the Markdown export as a file on disk:** Generate it dynamically from the database on each export request. No file storage needed.
- **Assuming competitor data always exists:** Some audits will have no crawled competitors. Gap analysis falls back to research benchmarks alone when `competitor_avg` is None.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LLM JSON parsing | Custom regex extraction | `json.loads(response.choices[0].message.content)` with `response_format={"type": "json_object"}` | LiteLLM JSON mode guarantees valid JSON output |
| Sentiment classification rules | VADER/TextBlob/keyword lists | LiteLLM zero-shot (gemini-2.5-flash) | Context-aware, ~92% accuracy at 3-class, cost ~$0.002 per audit |
| Recommendation deduplication | Bloom filter, similarity check | SHA-256 hash on (criterion_id + normalized_page_url) | Deterministic, stable across re-audits, O(1) lookup |
| Progress computation | Complex aggregation service | Simple `SELECT COUNT(*) WHERE status='done'` + total | Already have all data in AuditRecommendation table |
| Markdown generation | Template engine (Jinja2) | Python f-strings / string concatenation | No extra dependency; recommendations are structured data, not free-form |
| Accordion animation | JavaScript library | CSS `transition` + Vue `v-show` | Already used pattern in project; no additional JS bundle |

**Key insight:** This phase is primarily data transformation -- reading from Phase 6 and 7 tables, applying deterministic logic, and writing to new tables. Keep LLM usage to exactly two purposes: (1) sentiment classification of existing quotes, (2) optional content brief enrichment.

---

## Common Pitfalls

### Pitfall 1: Competitor Data May Not Exist
**What goes wrong:** `CompetitorAudit` records only exist if competitors were crawled. If crawl failed or user has no competitors, `competitor_avg` will be None for all recommendations.
**Why it happens:** Phase 7 makes competitor crawling best-effort (non-fatal).
**How to avoid:** Always fall back to research benchmarks when `competitor_avg` is None. The gap analysis must work with research benchmarks alone. A recommendation is still valid if criterion score is below threshold even without competitor comparison.
**Warning signs:** All `gap_score` values are None or 0.

### Pitfall 2: CriterionResult Records Per Page
**What goes wrong:** Recommendations must be page-specific, but criteria IDs may differ across scorers. If a page has no CriterionResult records (scoring failed), no recommendations are generated for that page.
**Why it happens:** Scoring is best-effort (conditional imports); a page might score 0 with empty criterion_results.
**How to avoid:** Check `CriterionResult` count before generating page recommendations. Log a warning if a scored page has no criteria results. Skip recommendation generation for that page.

### Pitfall 3: LiteLLM API Key Pattern
**What goes wrong:** Sentiment service forgets to pass `api_key=settings.GEMINI_API_KEY` explicitly. LiteLLM silently fails or picks wrong key.
**Why it happens:** `pydantic-settings` loads `.env` into the `Settings` object, NOT into `os.environ`. LiteLLM env var auto-detection won't find it.
**How to avoid:** Always use the pattern: `litellm.completion(model=..., api_key=settings.GEMINI_API_KEY, ...)`. This is already documented in MEMORY.md as a project-wide decision.
**Warning signs:** `AuthenticationError` from LiteLLM in logs.

### Pitfall 4: Recommendation Hash Collision
**What goes wrong:** Two different recommendations for different pages get the same hash if page URLs normalize identically.
**Why it happens:** URL normalization edge cases (e.g., `/page` vs `/page/` vs `/page?ref=1`).
**How to avoid:** Include query params in normalization? No -- strip them to keep it stable. Truncate hash to 16 chars = 2^64 space, collision probability negligible. Log a warning if hash already exists for same audit (indicates duplicate generation).

### Pitfall 5: Sentiment Analysis on Empty Mentions
**What goes wrong:** Sentiment service tries to classify when audit has zero brand mentions.
**Why it happens:** Audit with 0 mentions still has BrandMention records count = 0.
**How to avoid:** Guard clause at start of `analyze_audit_sentiments()`: if no mentions found, return empty list immediately. No LLM calls.

### Pitfall 6: AuditStatus.RECOMMENDING Not Registered
**What goes wrong:** Adding RECOMMENDING to AuditStatus enum but not to audit_tasks.py or frontend status polling.
**Why it happens:** Enum values are used in multiple places (tasks, frontend, API).
**How to avoid:** Update all places that handle AuditStatus: (a) audit_tasks.py pipeline, (b) frontend AuditProgress.vue status messages, (c) any status-filtering queries.

### Pitfall 7: JSONB content_gaps Column Migration
**What goes wrong:** Adding `content_gaps` JSONB to the `Audit` model without a migration.
**Why it happens:** Forgot to run `alembic revision --autogenerate` after model change.
**How to avoid:** Per project pattern, create migration manually (no local DB for autogenerate). Name it `009_add_content_gaps_and_recommendations.py`. Test with `docker-compose up`.

---

## Code Examples

### RecommendationEngine Core Gap Analysis

```python
# backend/app/services/recommendation_engine.py
# Source: Project patterns from scoring_orchestrator.py + competitor_service.py

from dataclasses import dataclass, field
from typing import Optional
import hashlib
from urllib.parse import urlparse

from loguru import logger
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.audit import Audit
from app.models.audit_recommendation import AuditRecommendation
from app.models.competitor import CompetitorAudit
from app.models.criterion_result import CriterionResult
from app.models.page_score import PageScore


# Hard-coded research benchmarks (from MEMORY.md research findings)
CRITERION_RESEARCH_MAP: dict[str, dict] = {
    "SD7": {"impact_pct": 320, "impact_label": "3.2x citation rate", "evidence_source": "BrightEdge + Frase.io", "priority_base": "high", "threshold": 60},
    "SD1": {"impact_pct": 240, "impact_label": "2.3-2.5x in AI Overviews", "evidence_source": "BrightEdge", "priority_base": "high", "threshold": 60},
    "CS1": {"impact_pct": 140, "impact_label": "+40% citations", "evidence_source": "Princeton GEO paper", "priority_base": "high", "threshold": 50},
    "CS4": {"impact_pct": 140, "impact_label": "+40% visibility", "evidence_source": "Princeton GEO paper", "priority_base": "medium", "threshold": 50},
    "CS8": {"impact_pct": 410, "impact_label": "4.1x AI citations", "evidence_source": "Surfer SEO 46M analysis", "priority_base": "high", "threshold": 40},
    "CS5": {"impact_pct": 120, "impact_label": "+15-25% boost", "evidence_source": "Princeton GEO paper", "priority_base": "medium", "threshold": 40},
    # Default for unlisted: impact_pct=105, priority_base="low", threshold=60
}
DEFAULT_BENCHMARK = {"impact_pct": 105, "impact_label": "+5% improvement", "evidence_source": "Industry standard", "priority_base": "low", "threshold": 60}


def _compute_rec_hash(criterion_id: str, page_url: str) -> str:
    parsed = urlparse(page_url.lower())
    normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"
    key = f"{criterion_id}|{normalized}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


class RecommendationEngine:
    def __init__(self, db: Session):
        self.db = db

    def generate_recommendations(self, audit_id: str, user_id: str) -> list[AuditRecommendation]:
        """Generate page-specific recommendations from scoring data."""
        # Load competitor category averages (may be empty)
        comp_audits = (
            self.db.query(CompetitorAudit)
            .filter(CompetitorAudit.parent_audit_id == audit_id)
            .filter(CompetitorAudit.status == "completed")
            .all()
        )

        # Compute competitor averages per category
        comp_avgs = self._compute_competitor_averages(comp_audits)

        # Load all scored pages
        page_scores = (
            self.db.query(PageScore)
            .filter(PageScore.audit_id == audit_id)
            .filter(PageScore.was_scored.is_(True))
            .all()
        )

        recs = []
        for page_score in page_scores:
            page_recs = self._generate_page_recommendations(
                audit_id, user_id, page_score, comp_avgs
            )
            recs.extend(page_recs)

        # Sort by priority then gap_score
        priority_order = {"high": 0, "medium": 1, "low": 2}
        recs.sort(key=lambda r: (priority_order.get(r.priority, 2), -r.gap_score))

        for rec in recs:
            self.db.add(rec)
        self.db.flush()
        return recs

    def _compute_competitor_averages(self, comp_audits: list) -> dict[str, Optional[float]]:
        """Average per-category scores across all crawled competitors."""
        categories = ["crawlability", "content_structure", "structured_data", "authority"]
        avgs = {}
        for cat in categories:
            scores = [getattr(ca, f"{cat}_avg") for ca in comp_audits if getattr(ca, f"{cat}_avg") is not None]
            avgs[cat] = sum(scores) / len(scores) if scores else None
        return avgs

    def _generate_page_recommendations(
        self, audit_id: str, user_id: str, page_score: PageScore, comp_avgs: dict
    ) -> list[AuditRecommendation]:
        """Generate recommendations for a single page."""
        criteria = (
            self.db.query(CriterionResult)
            .filter(CriterionResult.page_score_id == page_score.id)
            .filter(CriterionResult.checked.is_(True))
            .all()
        )

        recs = []
        for criterion in criteria:
            benchmark = CRITERION_RESEARCH_MAP.get(criterion.criterion_id, DEFAULT_BENCHMARK)
            threshold = benchmark["threshold"]

            if criterion.score >= threshold:
                continue  # Already good enough

            comp_avg = comp_avgs.get(criterion.category)
            gap_score = round((comp_avg - criterion.score) if comp_avg is not None else (threshold - criterion.score))

            if gap_score < 10:
                continue  # Gap too small to matter

            priority = self._classify_priority(benchmark["impact_pct"], gap_score)
            rec_hash = _compute_rec_hash(criterion.criterion_id, page_score.page_url)

            # Check for prior done/dismissed status
            status = self._lookup_prior_status(rec_hash, user_id) or "open"

            summary = self._build_summary(criterion, benchmark, comp_avg, page_score.page_url)

            rec = AuditRecommendation(
                audit_id=audit_id,
                page_url=page_score.page_url,
                criterion_id=criterion.criterion_id,
                criterion_name=criterion.criterion_name,
                category=criterion.category,
                priority=priority,
                impact_label=benchmark["impact_label"],
                impact_pct=benchmark["impact_pct"],
                user_score=criterion.score,
                competitor_avg=round(comp_avg) if comp_avg is not None else None,
                gap_score=gap_score,
                summary=summary,
                action_steps=self._build_action_steps(criterion, benchmark),
                code_snippet=self._build_code_snippet(criterion),
                evidence_source=benchmark["evidence_source"],
                recommendation_hash=rec_hash,
                status=status,
            )
            recs.append(rec)
        return recs

    def _classify_priority(self, impact_pct: int, gap_score: int) -> str:
        """High: impact>=200 and gap>=30 (or gap>=50). Medium: impact>=120 and gap>=20. Low: rest."""
        if gap_score >= 50 or (impact_pct >= 200 and gap_score >= 30):
            return "high"
        if impact_pct >= 120 and gap_score >= 20:
            return "medium"
        return "low"

    def _lookup_prior_status(self, rec_hash: str, user_id: str) -> Optional[str]:
        """Look up previous done/dismissed status for this recommendation hash."""
        from app.models.audit import Audit
        result = (
            self.db.query(AuditRecommendation.status)
            .join(Audit, AuditRecommendation.audit_id == Audit.id)
            .filter(Audit.user_id == user_id)
            .filter(AuditRecommendation.recommendation_hash == rec_hash)
            .filter(AuditRecommendation.status.in_(["done", "dismissed"]))
            .order_by(AuditRecommendation.created_at.desc())
            .first()
        )
        return result[0] if result else None
```

### LiteLLM Sentiment Classification

```python
# backend/app/services/sentiment_service.py
# Source: LiteLLM docs (https://docs.litellm.ai/docs/completion/json_mode)
# CRITICAL: Pass api_key explicitly -- pydantic-settings does NOT populate os.environ

import json
import litellm
from loguru import logger
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.brand_mention import BrandMention
from app.models.engine_response import EngineResponse
from app.models.audit_query import AuditQuery
from app.models.mention_sentiment import MentionSentiment


class SentimentService:
    SENTIMENT_MODEL = "gemini/gemini-2.5-flash"

    def __init__(self, db: Session):
        self.db = db

    def classify_mention_sentiment(self, context_quote: str) -> dict:
        """Classify a single mention's sentiment. Returns {"sentiment": ..., "confidence": ...}"""
        if not settings.GEMINI_API_KEY:
            return {"sentiment": "neutral", "confidence": 50}

        response = litellm.completion(
            model=self.SENTIMENT_MODEL,
            api_key=settings.GEMINI_API_KEY,
            response_format={"type": "json_object"},
            temperature=0.0,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a brand mention sentiment classifier. "
                        "Return only valid JSON: "
                        '{"sentiment": "positive" | "negative" | "neutral", "confidence": 0-100}'
                    ),
                },
                {
                    "role": "user",
                    "content": f'Classify the sentiment of this brand mention:\n"{context_quote}"',
                },
            ],
        )
        return json.loads(response.choices[0].message.content)

    def analyze_audit_sentiments(self, audit_id: str) -> list[MentionSentiment]:
        """Batch-classify all brand mentions for an audit."""
        mention_rows = (
            self.db.query(BrandMention, EngineResponse.engine)
            .join(EngineResponse, BrandMention.engine_response_id == EngineResponse.id)
            .join(AuditQuery, EngineResponse.audit_query_id == AuditQuery.id)
            .filter(AuditQuery.audit_id == audit_id)
            .all()
        )

        if not mention_rows:
            return []

        results = []
        for mention, engine in mention_rows:
            try:
                classification = self.classify_mention_sentiment(mention.context_quote)
                record = MentionSentiment(
                    audit_id=audit_id,
                    brand_mention_id=mention.id,
                    engine=engine,
                    sentiment=classification.get("sentiment", "neutral"),
                    confidence=classification.get("confidence", 50),
                    context_quote=mention.context_quote,
                )
                self.db.add(record)
                results.append(record)
            except Exception as e:
                logger.warning("Sentiment failed for mention {}: {}", mention.id, str(e))

        self.db.flush()
        return results

    def get_per_engine_summary(self, audit_id: str) -> dict[str, dict]:
        """Return per-engine sentiment breakdown for display."""
        from sqlalchemy import func
        rows = (
            self.db.query(
                MentionSentiment.engine,
                MentionSentiment.sentiment,
                func.count(MentionSentiment.id).label("count"),
            )
            .filter(MentionSentiment.audit_id == audit_id)
            .group_by(MentionSentiment.engine, MentionSentiment.sentiment)
            .all()
        )

        summary: dict[str, dict] = {}
        for engine, sentiment, count in rows:
            if engine not in summary:
                summary[engine] = {"positive": 0, "negative": 0, "neutral": 0, "total": 0}
            summary[engine][sentiment] = count
            summary[engine]["total"] += count

        # Add dominant sentiment
        for engine_data in summary.values():
            total = engine_data["total"]
            if total > 0:
                engine_data["dominant"] = max(
                    ["positive", "negative", "neutral"],
                    key=lambda s: engine_data[s]
                )
            else:
                engine_data["dominant"] = "neutral"

        return summary
```

### Alembic Migration Pattern (Manual, No Local DB)

```python
# backend/alembic/versions/009_add_recommendations_and_sentiments.py
"""Add audit_recommendations, mention_sentiments, content_gaps to audits

Revision ID: 009
Revises: 008
Create Date: 2026-02-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

def upgrade():
    # New audit_recommendations table
    op.create_table(
        "audit_recommendations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("audit_id", UUID(as_uuid=True), sa.ForeignKey("audits.id"), nullable=False, index=True),
        sa.Column("page_url", sa.String, nullable=True),
        sa.Column("criterion_id", sa.String, nullable=False),
        sa.Column("criterion_name", sa.String, nullable=False),
        sa.Column("category", sa.String, nullable=False),
        sa.Column("priority", sa.String, nullable=False),
        sa.Column("impact_label", sa.String, nullable=False),
        sa.Column("impact_pct", sa.Integer, nullable=True),
        sa.Column("user_score", sa.Integer, nullable=False),
        sa.Column("competitor_avg", sa.Integer, nullable=True),
        sa.Column("gap_score", sa.Integer, nullable=False),
        sa.Column("summary", sa.Text, nullable=False),
        sa.Column("action_steps", JSONB, nullable=False, server_default="[]"),
        sa.Column("code_snippet", sa.Text, nullable=True),
        sa.Column("evidence_source", sa.String, nullable=False),
        sa.Column("recommendation_hash", sa.String(16), nullable=False, index=True),
        sa.Column("status", sa.String, nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # New mention_sentiments table
    op.create_table(
        "mention_sentiments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("audit_id", UUID(as_uuid=True), sa.ForeignKey("audits.id"), nullable=False, index=True),
        sa.Column("brand_mention_id", UUID(as_uuid=True), sa.ForeignKey("brand_mentions.id"), nullable=False, unique=True),
        sa.Column("engine", sa.String, nullable=False),
        sa.Column("sentiment", sa.String, nullable=False),
        sa.Column("confidence", sa.Integer, nullable=False),
        sa.Column("context_quote", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # content_gaps JSONB column on audits
    op.add_column("audits", sa.Column("content_gaps", JSONB, nullable=True))

def downgrade():
    op.drop_column("audits", "content_gaps")
    op.drop_table("mention_sentiments")
    op.drop_table("audit_recommendations")
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| LLM-generated recommendations (free-form GPT-4 call) | Deterministic gap analysis + research benchmarks (no LLM for core) | Predictable, auditable, fast, no hallucination risk |
| Rule-based sentiment (VADER/TextBlob) | LLM zero-shot 3-class (gemini-2.5-flash) | ~92% accuracy vs ~65% VADER on contextual brand mentions |
| Generic "improve content" advice | Per-criterion evidence-backed recommendations with exact competitor comparison | Users know precisely what to fix and why |
| Manual recommendation creation | Pipeline-generated recommendations at audit completion | Zero user friction, always up-to-date |

**Legacy system to replace:** The existing `OptimizerService` in `backend/app/services/optimizer.py` and its `Recommendation` model (tied to `Analysis`) are legacy. Phase 8 does NOT use them. The new `AuditRecommendation` model is tied to `Audit`. The old `optimization.py` API router continues to exist (backward compat) but new recommendations are served from the new `recommendations.py` router.

---

## Open Questions

1. **Code snippet library for expanded view**
   - What we know: Each criterion has a `human_summary` and `technical_detail` field. Some criteria (like SD7 FAQPage) have well-defined code snippets.
   - What's unclear: Should code snippets be pre-defined per criterion (fast, accurate) or LLM-generated per page (personalized but costly)?
   - Recommendation: Pre-define code snippets for the top 10 highest-impact criteria in a `CRITERION_SNIPPETS` dict. For the remaining criteria, the action_steps list is sufficient without code.

2. **Content brief generation: LLM vs template**
   - What we know: User prefers briefs when possible. Template approach is free and instant. LLM adds ~$0.001/gap.
   - What's unclear: How many content gaps a typical audit generates (estimate: 3-15 gaps based on 15 queries and partial user visibility).
   - Recommendation: Start with template-based briefs (always works, zero cost). The LLM enrichment can be added as a background task if `GEMINI_API_KEY` is set, updating the `content_gaps` JSONB column with enriched briefs.

3. **AuditStatus.RECOMMENDING and frontend polling**
   - What we know: Frontend polls audit status during progress. A new RECOMMENDING status needs a user-facing message.
   - What's unclear: Does the frontend progress component already handle unknown status values gracefully?
   - Recommendation: Check `AuditProgress.vue` and add RECOMMENDING to the status message map. It should display "Generating recommendations..." with the spinner.

4. **Negative sentiment recommendation linking**
   - What we know: Negative mentions should trigger a specific recommendation (e.g., "ChatGPT says 'pricing is confusing' -- fix /pricing clarity").
   - What's unclear: How to link the sentiment record to a specific page recommendation. The mention has no page_url -- it comes from a query response, not a page crawl.
   - Recommendation: Negative sentiment records generate a special `AuditRecommendation` with `page_url=None` (site-wide) and `criterion_id="SENTIMENT"`. These appear in a dedicated "Negative Mentions" section separate from the page-specific recommendations.

---

## Sources

### Primary (HIGH confidence)

- Project codebase (verified by direct file reads):
  - `backend/app/services/scoring_orchestrator.py` -- page scoring patterns
  - `backend/app/services/competitor_service.py` -- competitor data structure
  - `backend/app/models/criterion_result.py` -- per-criterion scores
  - `backend/app/models/competitor.py` -- CompetitorAudit averages
  - `backend/app/models/brand_mention.py` -- context_quote source for sentiment
  - `backend/app/core/config.py` -- Settings, LiteLLM key pattern
  - `.planning/phases/08-actionable-recommendations/08-CONTEXT.md` -- user decisions
- LiteLLM documentation: https://docs.litellm.ai/docs/completion/json_mode -- JSON mode API verified
- Project MEMORY.md: LiteLLM api_key pattern (pydantic-settings, must pass explicitly)

### Secondary (MEDIUM confidence)

- Research impact stats (from MEMORY.md, sourced from:)
  - Princeton GEO paper: answer-first +40%, statistics +40%, quotations +15-25%
  - BrightEdge: JSON-LD 2.3-2.5x AI Overviews, FAQPage 3.2x citation rate
  - Frase.io: FAQPage +28% citations
  - Surfer SEO 46M analysis: data tables 4.1x AI citations
- Sentiment accuracy: GPT-4 3-class zero-shot ~92% (multiple sources; applied to gemini-2.5-flash, expected similar for simple brand sentiment)

### Tertiary (LOW confidence)

- Content gap card UX patterns from web search -- validate with design-system MASTER.md during implementation
- Accordion pattern (vue-show + CSS transition) -- widely documented, safe to use

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already installed and used in project
- Architecture (recommendation engine): HIGH -- direct reads from existing DB tables, no unknowns
- Architecture (sentiment): HIGH -- LiteLLM JSON mode verified, api_key pattern documented
- Architecture (content gaps): HIGH -- deterministic query cross-reference, data already in DB
- Architecture (export): HIGH -- simple string generation, no library needed
- Frontend patterns: MEDIUM -- project follows established Vue 3 + Tailwind patterns; specific component structures are reasonable but untested
- Research benchmarks: MEDIUM -- sourced from MEMORY.md which cites authoritative papers

**Research date:** 2026-02-22
**Valid until:** 2026-03-22 (30 days; stable domain, no fast-moving external APIs beyond LiteLLM)
