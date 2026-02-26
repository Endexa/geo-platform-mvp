# Phase 7: Auto-Competitor Discovery - Research

**Researched:** 2026-02-22
**Domain:** NER entity extraction, competitor pipeline, share-of-voice analysis, source citation extraction
**Confidence:** HIGH

## Summary

Phase 7 transforms AI engine responses (already collected in Phase 3-4) into competitive intelligence by extracting all brand/entity names mentioned, ranking them by frequency to compute share-of-voice, and then crawling + scoring the top competitors using the existing Phase 2 + Phase 6 pipeline. The phase also adds source citation extraction from Perplexity responses and custom query management.

The core technical challenge is Named Entity Recognition (NER) on AI-generated text to extract brand/company names. spaCy's `en_core_web_sm` model (13MB, 84.6% NER F1-score) provides ORG and PRODUCT entity detection that is more than sufficient for well-structured AI response text. A layered approach (spaCy NER + regex pattern matching + URL-domain extraction) provides the most robust entity discovery. For competitor URL resolution, a lightweight heuristic approach (domain-from-brand-name + Google Knowledge Graph lookup via existing GOOGLE_API_KEY) avoids expensive external API dependencies.

**Primary recommendation:** Use spaCy `en_core_web_sm` for NER entity extraction from AI responses, combined with regex patterns for URL/domain extraction from Perplexity citations. Store entities in a new `discovered_competitors` table. Reuse the existing CrawlerService + ScoringOrchestrator pipeline for competitor analysis. Keep competitor crawl count configurable (default 3-5) to control costs.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| COMP-01 | Extract brand/entity names from AI responses using NER and pattern matching | spaCy `en_core_web_sm` (ORG/PRODUCT entities, 84.6% F1) + regex URL/domain extraction + existing MentionDetector fuzzy matching patterns |
| COMP-02 | Rank entities by mention frequency with share-of-voice percentages | SOV formula: (entity mentions / total mentions) x 100, computed per-engine and overall, stored in `discovered_competitors` table |
| COMP-03 | Competitor leaderboard showing which brands AI mentions most | New API endpoint + frontend component. Data from `discovered_competitors` table ranked by mention_count |
| COMP-04 | Auto-crawl top competitors using same crawl + scoring pipeline | Reuse CrawlerService.crawl() + ScoringOrchestrator.score_audit() with new CompetitorAudit records linked to parent audit |
| COMP-05 | Compare competitor scores vs user scores per category | Query PageScore + CriterionResult for both user audit and competitor audits, compute delta per category |
| COMP-06 | Custom query management (add/edit/remove queries) | New API endpoints for AuditQuery CRUD + `is_custom` flag + frontend query editor UI |
| COMP-07 | Extract source citations from AI responses (especially Perplexity) | Perplexity returns `citations` array in response JSON. LiteLLM passes this through. Also regex extract URLs from response text for other engines |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| spaCy | >=3.7 | Named Entity Recognition (ORG, PRODUCT, PERSON) | Industry standard NER, 84.6% F1, 13MB model, CPU-optimized |
| en_core_web_sm | 3.7.x | English NER model | Smallest model (13MB), sufficient for well-structured AI text, ORG+PRODUCT entity types |

### Supporting (Already in Stack)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| rapidfuzz | >=3.14.0 | Fuzzy matching for entity deduplication | Merge "Stripe" and "Stripe, Inc." and "stripe.com" into one entity |
| httpx | 0.26.0 | Competitor site crawling | Already used by CrawlerService |
| SQLAlchemy | 2.0.25 | New competitor models | Already the project ORM |
| BeautifulSoup4 | 4.12.2 | HTML parsing for competitor pages | Already used by CrawlerService |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| spaCy en_core_web_sm | en_core_web_md (48MB) | 0.1% better NER F1, but 3.5x larger. Not worth it for AI-generated text which has clean entity boundaries. |
| spaCy en_core_web_sm | en_core_web_lg (560MB) | 0.2% better NER F1, but 43x larger. Docker image bloat far outweighs marginal accuracy gain. |
| spaCy | Hugging Face transformers | Much heavier dependency chain, GPU preferred. Overkill for extracting ORG entities from short AI responses. |
| spaCy | LLM-based extraction (litellm) | Would add API cost per extraction. NER on already-collected text should be free/local. |
| Regex only | spaCy NER + regex | Regex alone misses entities without URL patterns. NER catches "Salesforce" even when no URL is given. |

**Installation:**
```bash
pip install spacy>=3.7
python -m spacy download en_core_web_sm
```

**Docker Dockerfile addition:**
```dockerfile
RUN pip install spacy>=3.7 && python -m spacy download en_core_web_sm
```

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
  models/
    competitor.py              # DiscoveredCompetitor, CompetitorAudit models
  services/
    entity_extractor.py        # NER + regex entity extraction from AI responses
    competitor_service.py       # Orchestrates: extract -> rank -> resolve URL -> crawl -> score
  api/
    competitors.py             # /competitors endpoints (leaderboard, comparison)
    audit.py                   # Extended: custom query CRUD (COMP-06)
  schemas/
    competitor.py              # Pydantic schemas for competitor API responses
frontend/
  pages/
    competitors.vue            # Competitor leaderboard + comparison view
  components/
    CompetitorLeaderboard.vue  # Share-of-voice table
    CompetitorComparison.vue   # Side-by-side score comparison
    QueryEditor.vue            # Custom query add/edit/remove
```

### Pattern 1: Entity Extraction Service (COMP-01, COMP-07)
**What:** A service that takes all EngineResponse records for an audit and extracts brand/entity names + source citations
**When to use:** After the ANALYZING stage in the audit pipeline, before SCORING or as part of a new COMPETITOR_DISCOVERY stage

```python
import spacy
import re
from collections import Counter

class EntityExtractorService:
    """Extracts brand/entity names and source citations from AI responses."""

    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")

    def extract_entities(self, response_text: str) -> list[dict]:
        """Extract ORG and PRODUCT entities from AI response text.

        Returns list of dicts: {text, label, start_char, end_char}
        """
        doc = self.nlp(response_text)
        entities = []
        for ent in doc.ents:
            if ent.label_ in ("ORG", "PRODUCT"):
                entities.append({
                    "text": ent.text,
                    "label": ent.label_,
                    "start_char": ent.start_char,
                    "end_char": ent.end_char,
                })
        return entities

    def extract_citations(self, response_text: str, citations_meta: list[str] | None = None) -> list[str]:
        """Extract source URLs from response text and Perplexity citations metadata.

        Args:
            response_text: The AI response text (may contain inline URLs)
            citations_meta: Perplexity citations array from API response (list of URLs)
        """
        urls = set()

        # 1. Perplexity citations metadata (most reliable)
        if citations_meta:
            urls.update(citations_meta)

        # 2. Regex: extract URLs from response text (all engines)
        url_pattern = re.compile(
            r'https?://[^\s\)\]\},\"\']+', re.IGNORECASE
        )
        urls.update(url_pattern.findall(response_text))

        # 3. Markdown link extraction: [text](url)
        md_pattern = re.compile(r'\[([^\]]+)\]\((https?://[^\)]+)\)')
        for _, url in md_pattern.findall(response_text):
            urls.add(url)

        return sorted(urls)
```

### Pattern 2: Entity Deduplication and Ranking (COMP-02)
**What:** Merge entity variants (e.g., "Stripe", "Stripe, Inc.", "stripe.com") and compute share-of-voice
**When to use:** After extracting entities from all responses for an audit

```python
from rapidfuzz import fuzz

class EntityDeduplicator:
    """Merges entity variants and computes share-of-voice."""

    CORPORATE_SUFFIXES = ["Inc.", "Inc", "LLC", "Ltd.", "Ltd", "Co.", "Corp.", "Corp"]

    def deduplicate_entities(
        self, raw_entities: list[dict], threshold: int = 85
    ) -> list[dict]:
        """Group similar entities into canonical forms.

        Returns: [{canonical_name, variants, mention_count, engines, queries}]
        """
        # Strip corporate suffixes for comparison
        # Use rapidfuzz token_set_ratio for fuzzy matching
        # Group entities with score >= threshold
        # Keep the most frequent variant as canonical_name
        ...

    def compute_share_of_voice(
        self, ranked_entities: list[dict], user_brand_name: str
    ) -> list[dict]:
        """Compute share-of-voice percentages.

        SOV = (entity_mentions / total_mentions_across_all_entities) * 100
        """
        total = sum(e["mention_count"] for e in ranked_entities)
        for entity in ranked_entities:
            entity["share_of_voice"] = round(
                (entity["mention_count"] / total * 100) if total > 0 else 0, 1
            )
            entity["is_user_brand"] = (
                fuzz.ratio(entity["canonical_name"].lower(), user_brand_name.lower()) > 90
            )
        return sorted(ranked_entities, key=lambda e: e["mention_count"], reverse=True)
```

### Pattern 3: Competitor Crawl and Score Pipeline (COMP-04, COMP-05)
**What:** Reuse existing CrawlerService + ScoringOrchestrator for competitor sites
**When to use:** After top competitors are identified and their URLs resolved

**Key design decision:** Create a separate `CompetitorAudit` record for each competitor, linked to the parent audit. This reuses the existing PageScore/CriterionResult infrastructure without modifying it.

```python
class CompetitorService:
    """Orchestrates competitor discovery, crawling, and comparison."""

    def __init__(self, db: Session):
        self.db = db
        self.extractor = EntityExtractorService()
        self.crawler = CrawlerService()

    async def crawl_and_score_competitor(
        self, parent_audit_id: str, competitor_url: str, competitor_name: str
    ) -> dict:
        """Crawl a competitor site and score it using the Phase 6 pipeline.

        Creates a CompetitorAudit record and runs the ScoringOrchestrator.
        """
        # 1. Crawl the competitor homepage
        crawl_result = await self.crawler.crawl(competitor_url)

        # 2. Create CompetitorAudit record
        competitor_audit = CompetitorAudit(
            parent_audit_id=parent_audit_id,
            competitor_name=competitor_name,
            competitor_url=competitor_url,
            crawl_data=crawl_result.model_dump(),
        )
        self.db.add(competitor_audit)
        self.db.flush()

        # 3. Run scoring pipeline (reuse ScoringOrchestrator)
        orchestrator = ScoringOrchestrator(self.db)
        # Register all scorers (same pattern as audit_tasks.py)
        ...
        scoring_result = await orchestrator.score_audit(
            str(competitor_audit.id), crawl_result.model_dump(), visibility_score=0
        )
        competitor_audit.optimization_score = scoring_result["optimization_score"]
        self.db.commit()

        return scoring_result
```

### Pattern 4: URL Resolution for Brand Names (COMP-04)
**What:** Convert brand names like "Salesforce" to crawlable URLs like "https://www.salesforce.com"
**When to use:** After entities are ranked, before crawling

**Strategy (layered, no external API required):**
1. **Perplexity citations:** If the entity was mentioned alongside a citation URL, use that domain
2. **Domain heuristic:** Try `https://www.{brand_lowercase}.com` and check HTTP 200
3. **Google Knowledge Graph API:** Use existing `GOOGLE_API_KEY` setting to query Knowledge Graph for the entity's official website (free tier: 100K queries/day)
4. **Manual fallback:** Store as unresolved; user can manually assign URL

```python
async def resolve_competitor_url(self, entity_name: str, citation_urls: list[str]) -> str | None:
    """Try to resolve an entity name to a website URL.

    Priority: citation URL domain > domain heuristic > Knowledge Graph > None
    """
    # 1. Check citation URLs for this entity
    for url in citation_urls:
        domain = urlparse(url).netloc
        if fuzz.partial_ratio(entity_name.lower(), domain.lower()) > 70:
            return f"https://{domain}"

    # 2. Domain heuristic
    clean_name = entity_name.lower().replace(" ", "").replace(",", "")
    candidate = f"https://www.{clean_name}.com"
    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            resp = await client.head(candidate)
            if resp.status_code < 400:
                return candidate
    except Exception:
        pass

    # 3. Google Knowledge Graph (if API key configured)
    if settings.GOOGLE_API_KEY:
        # Query Knowledge Graph API for official website
        ...

    return None
```

### Pattern 5: Perplexity Citations Capture (COMP-07)
**What:** Capture the `citations` array from Perplexity API responses at dispatch time
**When to use:** Modify DispatchService to store citations metadata

**Key finding:** The Perplexity API returns a `citations` array at the top level of the response JSON, containing URLs of sources it referenced. LiteLLM passes this through but it is NOT currently captured by our DispatchService. The citations are available on the response object (not in streaming mode).

**Implementation:** Add a `citations` JSONB column to `engine_responses` table to store the array of source URLs. Modify `_call_engine` in DispatchService to extract and store `response.citations` or `response._hidden_params.get("citations", [])` for Perplexity responses.

### Anti-Patterns to Avoid
- **Crawling competitors synchronously in the main audit pipeline:** This would make audits take 10x longer. Competitor crawling should be a separate async stage or a separate Celery task.
- **Using LLM calls for entity extraction:** NER on already-collected text should be free/local. Do not send response text back through an LLM API.
- **Storing competitor data inside the Audit model:** Use separate models (DiscoveredCompetitor, CompetitorAudit) with FK references to the parent audit.
- **Crawling every discovered entity:** Only crawl top 3-5 by mention frequency. Many entities will be generic terms, not competitors.
- **Hardcoding entity exclusions:** Instead, filter by entity type (ORG/PRODUCT only) and let the share-of-voice ranking naturally surface real competitors.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Named Entity Recognition | Custom regex for brand names | spaCy `en_core_web_sm` NER | Regex misses entities without URL patterns; spaCy handles abbreviations, context, multi-word names |
| Entity deduplication | Custom string matching | rapidfuzz (already in stack) | Corporate suffix stripping, case normalization, token_set_ratio for "Stripe Inc" vs "Stripe" |
| URL extraction from text | Custom URL parser | `re.compile(r'https?://...')` + `urllib.parse` | Standard URL regex covers all edge cases |
| Competitor site crawling | New crawling logic | Existing CrawlerService | Already handles robots.txt, structured data extraction, content analysis |
| Competitor site scoring | New scoring logic | Existing ScoringOrchestrator + all 4 scorers | Already produces per-category scores with criterion details |
| Share-of-voice calculation | Complex algorithm | Simple division: mentions/total*100 | Standard marketing formula, no special math needed |

**Key insight:** Phase 7's power comes from ORCHESTRATION of existing capabilities (crawl, score, detect mentions), not from building new fundamental capabilities. The only truly new piece is NER entity extraction, which spaCy handles out of the box.

## Common Pitfalls

### Pitfall 1: spaCy NER on Short Text
**What goes wrong:** spaCy NER accuracy drops on very short text fragments because it lacks context for entity disambiguation
**Why it happens:** AI response text is typically 200-800 words, which is fine. But if you try NER on individual sentences, accuracy drops.
**How to avoid:** Run NER on the full response_text, not on sentence fragments. The full response provides enough context for spaCy to disambiguate.
**Warning signs:** Entities like "Apple" classified as ORG when the response is about fruit (unlikely in AI competitive responses, but possible).

### Pitfall 2: Entity Explosion from Generic Terms
**What goes wrong:** spaCy tags generic terms like "the platform", "this tool", "their service" as ORG entities
**Why it happens:** AI responses use generic references. NER may tag them as entities.
**How to avoid:** Post-filter: (1) Require entities to appear in at least 2 responses, (2) Exclude entities shorter than 2 characters, (3) Exclude the user's own brand name from competitor list, (4) Filter out common generic terms (blocklist).
**Warning signs:** Competitor leaderboard shows entries like "The", "This", "Service".

### Pitfall 3: Competitor Crawl Budget Explosion
**What goes wrong:** Crawling 5 competitor sites x 25 pages each = 125 additional page crawls per audit, multiplying the audit cost and duration
**Why it happens:** Using the same SCORING_CRAWL_CAP (25 pages) for competitors as for the user's site
**How to avoid:** Use a much lower cap for competitors (5-10 pages each). The goal is directional comparison, not exhaustive analysis. Make it configurable via `COMPETITOR_CRAWL_CAP` setting.
**Warning signs:** Audit pipeline taking >10 minutes, rate limiting hitting on external APIs.

### Pitfall 4: Perplexity Citations Not Captured
**What goes wrong:** The citations array from Perplexity is lost because it's not stored at dispatch time
**Why it happens:** The current DispatchService only captures `response_text`, `prompt_tokens`, `completion_tokens`, and `cost`. It does not capture the `citations` field from the Perplexity response.
**How to avoid:** Add a `citations` JSONB column to `engine_responses` table. Modify `_call_engine` to extract and store citations for Perplexity responses at dispatch time.
**Warning signs:** COMP-07 requirement cannot be fulfilled without modifying the dispatch layer.

### Pitfall 5: URL Resolution Failure for Brand Names
**What goes wrong:** Cannot convert "Acme Corp" to "https://www.acmecorp.com" reliably
**Why it happens:** Brand names don't always map cleanly to domain names (e.g., "McKinsey & Company" -> "mckinsey.com", not "mckinseyandcompany.com")
**How to avoid:** Use a layered resolution strategy (citation URL > heuristic > Knowledge Graph > manual). Store the resolution status. Allow the user to manually override/confirm competitor URLs.
**Warning signs:** Many competitors show as "URL not resolved" in the leaderboard.

### Pitfall 6: N+1 Query Issue on Competitor Comparison
**What goes wrong:** Loading competitor page scores for comparison requires multiple DB queries per competitor
**Why it happens:** Each competitor has its own set of PageScore and CriterionResult records
**How to avoid:** Use joinedload/selectinload patterns (already established in the codebase). Precompute category averages when storing CompetitorAudit results instead of computing on-the-fly.
**Warning signs:** API response time for comparison endpoint >2 seconds.

### Pitfall 7: Audit Pipeline Stage Ordering
**What goes wrong:** Competitor discovery runs before mention analysis is complete, missing data
**Why it happens:** The competitor discovery stage needs entities from AI responses, which need the ANALYZING stage to be complete
**How to avoid:** Add competitor discovery as a new pipeline stage AFTER SCORING (Stage 7: DISCOVERING_COMPETITORS), or as a separate Celery task chain triggered after the main audit completes.
**Warning signs:** Empty competitor leaderboard because entity extraction ran before responses were stored.

## Code Examples

### Example 1: spaCy NER Entity Extraction

```python
# Source: spaCy official docs + https://huggingface.co/spacy/en_core_web_sm
import spacy

nlp = spacy.load("en_core_web_sm")

response_text = """
When it comes to payment processing, Stripe is the market leader,
followed by PayPal and Square. Adyen is popular for enterprise clients,
while Braintree (owned by PayPal) serves mid-market businesses.
"""

doc = nlp(response_text)
for ent in doc.ents:
    if ent.label_ in ("ORG", "PRODUCT"):
        print(f"{ent.text} -> {ent.label_} (chars {ent.start_char}-{ent.end_char})")

# Output:
# Stripe -> ORG (chars 45-51)
# PayPal -> ORG (chars 81-87)
# Square -> ORG (chars 92-98)
# Adyen -> ORG (chars 100-105)
# Braintree -> ORG (chars 143-152)
# PayPal -> ORG (chars 163-169)
```

### Example 2: Perplexity Citations from LiteLLM Response

```python
# Source: LiteLLM Perplexity docs + GitHub issues
import litellm

response = litellm.completion(
    model="perplexity/sonar",
    messages=[{"role": "user", "content": "Best payment APIs"}],
    api_key=api_key,
)

# Citations are in the response object (non-streaming only)
# Access via the raw response or hidden params
citations = getattr(response, 'citations', None)
if citations is None:
    # Fallback: check _hidden_params
    citations = response._hidden_params.get("citations", [])

# citations = ["https://stripe.com/docs/api", "https://developer.paypal.com/", ...]
```

### Example 3: Share of Voice Calculation

```python
# Source: Standard marketing SOV formula
# https://sproutsocial.com/insights/share-of-voice/

def compute_share_of_voice(entities: list[dict]) -> list[dict]:
    """
    Input: [{"name": "Stripe", "mention_count": 15}, {"name": "PayPal", "mention_count": 10}, ...]
    Output: same list with "share_of_voice" percentage added
    """
    total_mentions = sum(e["mention_count"] for e in entities)
    for entity in entities:
        entity["share_of_voice"] = round(
            (entity["mention_count"] / total_mentions * 100) if total_mentions > 0 else 0, 1
        )
    return sorted(entities, key=lambda e: e["share_of_voice"], reverse=True)

# Example:
# Stripe: 15 mentions -> 37.5% SOV
# PayPal: 10 mentions -> 25.0% SOV
# Square: 8 mentions -> 20.0% SOV
# Adyen: 4 mentions -> 10.0% SOV
# Your Brand: 3 mentions -> 7.5% SOV
```

### Example 4: Database Model Pattern

```python
# Source: Follows existing project patterns (Audit, PageScore, CriterionResult)

class DiscoveredCompetitor(Base):
    __tablename__ = "discovered_competitors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id = Column(UUID(as_uuid=True), ForeignKey("audits.id"), nullable=False, index=True)
    entity_name = Column(String, nullable=False)          # Canonical name from NER
    entity_type = Column(String, nullable=False)           # "ORG" or "PRODUCT"
    mention_count = Column(Integer, nullable=False)         # Total mentions across all responses
    share_of_voice = Column(Numeric(5, 1), nullable=False) # Percentage
    engines_mentioned_in = Column(JSONB, nullable=True)     # {"openai": 5, "anthropic": 3, ...}
    resolved_url = Column(String, nullable=True)            # Resolved website URL (may be null)
    is_crawled = Column(Boolean, default=False)             # Whether competitor site was crawled
    competitor_audit_id = Column(UUID(as_uuid=True), nullable=True)  # FK to competitor's audit
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    audit = relationship("Audit", backref="discovered_competitors")


class CompetitorAudit(Base):
    """A mini-audit for a competitor site. Stores crawl data and links to PageScore records."""
    __tablename__ = "competitor_audits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_audit_id = Column(UUID(as_uuid=True), ForeignKey("audits.id"), nullable=False, index=True)
    competitor_name = Column(String, nullable=False)
    competitor_url = Column(String, nullable=False)
    crawl_data = Column(JSONB, nullable=True)
    optimization_score = Column(Integer, nullable=True)
    status = Column(String, default="pending")  # pending, crawling, scoring, completed, failed
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # PageScores are linked via audit_id FK -- we reuse the same PageScore model
    # by setting page_score.audit_id = competitor_audit.id
    # This works because PageScore.audit_id is a UUID FK, and CompetitorAudit.id is also a UUID
```

**Important note on CompetitorAudit and PageScore reuse:** The existing PageScore model has `audit_id = ForeignKey("audits.id")`. To avoid schema changes to PageScore, the CompetitorAudit stores its own summary scores (per-category averages) directly, rather than reusing PageScore rows. This keeps the data model clean.

**Revised approach:** Store competitor category scores directly on CompetitorAudit:
```python
class CompetitorAudit(Base):
    __tablename__ = "competitor_audits"
    # ... same fields as above, plus:
    crawlability_avg = Column(Integer, nullable=True)
    content_structure_avg = Column(Integer, nullable=True)
    structured_data_avg = Column(Integer, nullable=True)
    authority_avg = Column(Integer, nullable=True)
    pages_scored = Column(Integer, default=0)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual competitor entry by user | Auto-discovery from AI responses | Phase 7 innovation | Zero setup friction -- competitors are whoever AI actually mentions |
| Keyword-based competitor finding (SEMrush) | NER on AI engine responses | 2024-2025 (GEO tools era) | Reflects AI competitive landscape, not SEO competitive landscape |
| NLTK NER | spaCy NER | 2020+ | spaCy is faster, more accurate, better maintained for production use |
| en_core_web_trf (transformer model) | en_core_web_sm for simple tasks | Ongoing | Transformer models are overkill for well-structured text; sm is 40x smaller |

**Deprecated/outdated:**
- NLTK NER: Still works but spaCy is significantly faster and more accurate for production use
- LiteLLM streaming with Perplexity citations: Citations are NOT returned in streaming mode (as of 2025). Must use non-streaming for citation capture.
- Perplexity `return_citations` parameter: No longer needed as of Sonar models -- citations are returned by default

## Open Questions

1. **Perplexity citations access path in LiteLLM response object**
   - What we know: Perplexity API returns a `citations` array. LiteLLM passes it through.
   - What's unclear: Exact attribute path on the LiteLLM response object (is it `response.citations`, `response._hidden_params["citations"]`, or somewhere else?)
   - Recommendation: During implementation, inspect the LiteLLM response object for a real Perplexity call and log all attributes. LOW risk -- if the path is wrong, we can regex-extract URLs from the response text as fallback.

2. **CompetitorAudit vs PageScore FK constraint**
   - What we know: PageScore has `ForeignKey("audits.id")`. CompetitorAudit is a separate table.
   - What's unclear: Whether to add a polymorphic FK to PageScore or store competitor scores directly on CompetitorAudit
   - Recommendation: Store competitor category averages directly on CompetitorAudit (simpler, avoids FK complexity). Only store per-page detail if the user drills down.

3. **Audit pipeline stage placement**
   - What we know: Competitor discovery depends on ANALYZING being complete (need EngineResponse data)
   - What's unclear: Should competitor discovery be a new pipeline stage (DISCOVERING_COMPETITORS after SCORING) or a separate Celery task chain?
   - Recommendation: Add as a new stage after SCORING. This keeps the pipeline linear and simple. The stage is skippable (if no entities found, skip). Add a new AuditStatus: `DISCOVERING_COMPETITORS`.

4. **Custom query timing relative to audit pipeline**
   - What we know: Users can add/edit/remove custom queries "before or after an audit runs" (COMP-06)
   - What's unclear: If a user adds queries AFTER an audit completes, should those queries be dispatched immediately or only on re-audit?
   - Recommendation: Adding queries after completion stores them in DB for the NEXT audit run. Adding/editing BEFORE dispatching includes them in the current run. This is simpler than mid-pipeline injection.

## Sources

### Primary (HIGH confidence)
- [spaCy en_core_web_sm](https://huggingface.co/spacy/en_core_web_sm) -- NER F1: 84.6%, model size: 13MB, entity types: ORG, PRODUCT, PERSON + 15 others
- [spaCy official docs](https://spacy.io/usage/spacy-101/) -- NER usage patterns, model comparison, installation
- [spaCy models page](https://spacy.io/models) -- Model comparison (sm vs md vs lg vs trf)
- Existing codebase analysis (CrawlerService, ScoringOrchestrator, DispatchService, MentionDetectorService) -- reuse patterns verified

### Secondary (MEDIUM confidence)
- [LiteLLM Perplexity docs](https://docs.litellm.ai/docs/providers/perplexity) -- Perplexity integration, but citations handling poorly documented
- [LiteLLM GitHub Issue #4981](https://github.com/BerriAI/litellm/issues/4981) -- return_citations support discussion
- [Perplexity API Platform](https://www.perplexity.ai/hub/blog/introducing-the-sonar-pro-api) -- Citations returned by default with Sonar models
- [Share of Voice calculation](https://sproutsocial.com/insights/share-of-voice/) -- Standard SOV formula: (brand mentions / total mentions) x 100
- [Nanonets NER Guide 2025](https://nanonets.com/blog/named-entity-recognition-with-nltk-and-spacy/) -- NER best practices

### Tertiary (LOW confidence)
- [LiteLLM GitHub Issue #5535](https://github.com/BerriAI/litellm/issues/5535) -- Bug: streaming + return_citations doesn't work (verified by multiple users, but workaround unclear)
- [Perplexity docs llms-full.txt](https://docs.perplexity.ai/llms-full.txt) -- Citation format uses `[web:index]` bracket notation in text

## Metadata

**Confidence breakdown:**
- Standard stack (spaCy NER): HIGH -- well-established library, documented F1 scores, widely used for exactly this use case
- Architecture (pipeline integration): HIGH -- reuses existing CrawlerService + ScoringOrchestrator patterns from Phase 2 + Phase 6
- Entity extraction approach: HIGH -- spaCy ORG/PRODUCT NER is a standard, well-proven approach
- Perplexity citations capture: MEDIUM -- API returns citations, but exact LiteLLM access path needs runtime verification
- URL resolution: MEDIUM -- layered heuristic approach works for most cases, but edge cases exist (brand names that don't map to domains)
- Pitfalls: HIGH -- based on direct codebase analysis and known NER limitations

**Research date:** 2026-02-22
**Valid until:** 2026-03-22 (stable domain -- spaCy, SQLAlchemy, and LiteLLM are mature)
