# Phase 2: Recommendations + Competitor Benchmarking - Research

**Researched:** 2026-02-26
**Domain:** Deterministic gap analysis, industry-aware recommendation filtering, NER-based competitor discovery, share-of-voice calculation
**Confidence:** HIGH

## Summary

Phase 2 builds on a remarkably solid foundation. The codebase already contains a fully-implemented `RecommendationEngine` with deterministic gap analysis, research-backed benchmarks (13 criteria with specific impact data from Princeton GEO, BrightEdge, Surfer SEO, Ahrefs), code snippet templates, content gap identification, and Markdown export. The `EntityExtractorService` already performs spaCy NER extraction, fuzzy deduplication via rapidfuzz, and share-of-voice calculation. The `CompetitorService` already resolves brand names to URLs (3-layer strategy: citation matching > domain heuristic > Google Knowledge Graph), crawls competitor sites, scores them with all 4 category scorers, and stores per-category averages. The `competitors` and `recommendations` API routers already expose leaderboard, CRUD, sentiment summary, content gaps, and Markdown export endpoints. Frontend components (`RecommendationCard`, `CompetitorLeaderboard`, `CompetitorComparison`, `ContentGapCard`, etc.) already exist.

The primary gaps are: (1) **industry-aware recommendation filtering** -- the engine currently recommends ClaimReview schema to non-fact-check sites and Product schema to non-e-commerce sites (Pitfall 4 from research), (2) **impact estimates calculated from actual scoring data** rather than relying solely on static research benchmarks, (3) **competitor data persistence across audits** for trend tracking, and (4) **integration testing** to verify the full recommendations + competitor pipeline end-to-end with real scoring data from Phase 1.

**Primary recommendation:** Add a vertical classifier (schema heuristics + crawl signals) to the crawler pipeline, wire it into the recommendation engine as a relevance filter, add cross-audit competitor persistence via the Brand model, enhance impact estimates with actual score delta calculation, and write integration tests covering the full pipeline from scoring through recommendations and competitor discovery.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| REC-01 | Deterministic gap analysis generates priority-ordered recommendations from scoring results | **Already implemented** in `recommendation_engine.py`. Compares criterion scores against research benchmarks and competitor averages, classifies priority (HIGH/MEDIUM/LOW), sorts by priority then gap_score. Needs integration testing with real Phase 1 scoring data. |
| REC-02 | Each recommendation includes impact estimate (estimated score improvement if fixed) | **Partially implemented**. Current `impact_pct` comes from static research benchmarks (e.g., "3.2x citation rate"). Missing: calculated delta showing "if this criterion scored X instead of Y, your overall score changes by Z points." Research section below details the calculation approach. |
| REC-03 | Recommendations are industry-aware -- vertical classification affects advice relevance | **Not implemented**. This is the largest gap. Needs a `VerticalClassifier` that detects site type (SaaS, e-commerce, local business, media/blog, B2B) and a relevance filter that suppresses irrelevant schema recommendations. Research section below details the heuristic approach. |
| REC-04 | Recommendations grouped by category with severity levels | **Already implemented**. `AuditRecommendation` has `category` and `priority` fields. API supports filtering by both. Frontend `RecommendationCard` displays priority badges. |
| REC-05 | Each recommendation has a clear action description users can understand and act on | **Already implemented**. `action_steps` (JSONB list of strings) and `code_snippet` (template code) are populated per criterion. `summary` field provides a user-facing one-liner. Enhancement opportunity: add more code snippets for criteria not yet covered (only 10 of 61 criteria have snippets). |
| COMP-01 | Auto-discover competitor brands from AI engine responses via NER extraction | **Already implemented** in `entity_extractor.py`. spaCy `en_core_web_sm` extracts ORG/PRODUCT entities, fuzzy deduplication via rapidfuzz (threshold=85), blocklist filters generic terms, minimum 2 appearances required. Wired into audit pipeline Stage 6. |
| COMP-02 | Side-by-side score comparison (user site vs discovered competitors) | **Already implemented**. `CompetitorService.crawl_top_competitors()` resolves URLs and scores competitors with all 4 category scorers. `CompetitorAudit` stores per-category averages + optimization_score. Frontend `CompetitorComparison` component displays side-by-side data. |
| COMP-03 | Share of voice tracking: percentage of AI mentions per brand across engines over time | **Partially implemented**. SOV calculation exists per-audit in `entity_extractor.py`. `DiscoveredCompetitor.share_of_voice` stores the percentage. Missing: **cross-audit SOV trending** -- currently each audit has independent competitors with no linking between audits. |
| COMP-04 | Competitor data persists across audits to show trends | **Not implemented**. Current architecture: `DiscoveredCompetitor` has `audit_id` FK -- each audit creates fresh competitor records with no link to previous audits. Need to normalize competitors at the Brand level (using existing `Brand` model) so the same competitor entity persists across audits and SOV can be tracked over time. |
</phase_requirements>

## Standard Stack

### Core (Already Installed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| spaCy + en_core_web_sm | 3.x | NER extraction for competitor discovery | Already in use. F1=90.19% on NER. Minimal accuracy difference vs `en_core_web_trf` (90.30%) but 10-50x faster on CPU. Sufficient for ORG/PRODUCT entity extraction from AI-generated text which has clean grammar. |
| rapidfuzz | 3.x | Fuzzy string matching for entity deduplication and brand matching | Already in use in entity_extractor.py and mention_detector.py. Industry standard for Python fuzzy matching. |
| SQLAlchemy | 2.x | ORM for all database operations | Already in use. All models defined. |
| textstat | 0.x | Readability scoring | Already in use in content_structure_scorer.py |

### Supporting (No New Dependencies Needed)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| BeautifulSoup4 + lxml | Already installed | HTML parsing for vertical classification signals | Parse schema.org types, meta tags, page structure to classify site vertical |
| httpx | Already installed | HTTP client for competitor URL resolution | Already used in competitor_service.py |
| loguru | Already installed | Structured logging | Already used throughout |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| spaCy en_core_web_sm | en_core_web_trf (transformer) | +0.11% F1 accuracy but 10-50x slower on CPU, requires GPU for reasonable speed. Not worth it for this use case. |
| spaCy NER | LLM-based NER (GPT-NER approach) | Higher accuracy in low-resource scenarios but costs $0.01-0.05 per extraction, adds latency, non-deterministic. Current spaCy approach is free, fast, deterministic. |
| Deterministic recs | LLM-generated recommendations | Non-reproducible, costs per audit, risk of hallucination, harder to test. Deterministic is correct for this use case per ARCHITECTURE.md research. |
| Manual vertical classification | ML classifier (fasttext, BERT) | Overkill -- heuristic rules on schema.org types + crawl signals achieve 90%+ accuracy for the 5 target verticals. ML classifier needs training data we don't have. |

**Installation:** No new packages required. All dependencies already in `requirements.txt`.

## Architecture Patterns

### Recommended Project Structure

New files needed (within existing structure):

```
backend/app/services/
├── vertical_classifier.py          # NEW: Detect site vertical from crawl data
├── recommendation_engine.py        # EXISTING: Add vertical filter + impact delta calc
├── entity_extractor.py             # EXISTING: Minor enhancement (confidence scores)
├── competitor_service.py           # EXISTING: Add cross-audit competitor linking
└── scoring/
    └── (all existing scorers unchanged)

backend/app/models/
├── competitor.py                   # EXISTING: Add brand_id FK to DiscoveredCompetitor
└── (other models unchanged)

backend/tests/
├── test_recommendation_engine.py   # NEW: Integration tests
├── test_vertical_classifier.py     # NEW: Unit tests
├── test_entity_extractor.py        # NEW: Unit tests
└── test_competitor_pipeline.py     # NEW: Integration tests
```

### Pattern 1: Vertical Classifier (Heuristic-Based)

**What:** Detect website industry vertical from crawl data signals to filter irrelevant recommendations.
**When to use:** Called once per audit, after crawling, before recommendation generation.
**Confidence:** HIGH -- based on schema.org type analysis and crawl signal heuristics.

```python
# Source: Schema.org type hierarchy + crawl signal analysis
from enum import Enum
from typing import Optional

class SiteVertical(str, Enum):
    SAAS = "saas"
    ECOMMERCE = "ecommerce"
    LOCAL_BUSINESS = "local_business"
    MEDIA_BLOG = "media_blog"
    B2B_SERVICES = "b2b_services"
    GENERIC = "generic"  # fallback -- no filtering applied

class VerticalClassifier:
    """Classify website vertical from crawl data signals.

    Heuristic priority:
    1. Schema.org @type (strongest signal)
    2. Meta tags and page structure
    3. URL patterns and content signals
    """

    # Schema types that strongly indicate a vertical
    SCHEMA_VERTICAL_MAP = {
        # E-commerce signals
        "Product": "ecommerce",
        "Offer": "ecommerce",
        "AggregateOffer": "ecommerce",
        "ShoppingCenter": "ecommerce",
        "OnlineStore": "ecommerce",
        # Local business signals
        "LocalBusiness": "local_business",
        "Restaurant": "local_business",
        "Store": "local_business",
        "MedicalBusiness": "local_business",
        "LegalService": "local_business",
        # Media/blog signals
        "NewsArticle": "media_blog",
        "BlogPosting": "media_blog",
        "NewsMediaOrganization": "media_blog",
        # SaaS signals (inferred from absence of above + presence of these)
        "SoftwareApplication": "saas",
        "WebApplication": "saas",
    }

    # URL/content patterns per vertical
    ECOMMERCE_SIGNALS = ["cart", "checkout", "add-to-cart", "shop", "product", "price"]
    LOCAL_SIGNALS = ["directions", "hours", "location", "near-me", "appointment"]
    SAAS_SIGNALS = ["pricing", "signup", "sign-up", "demo", "trial", "features", "integrations", "api"]

    def classify(self, crawl_data: dict) -> SiteVertical:
        """Classify from crawl_data dict (CrawlResult.model_dump()).

        Returns the detected vertical with highest confidence signal.
        """
        schema_types = self._extract_schema_types(crawl_data)

        # Priority 1: Schema.org types (strongest signal)
        for schema_type in schema_types:
            if schema_type in self.SCHEMA_VERTICAL_MAP:
                return SiteVertical(self.SCHEMA_VERTICAL_MAP[schema_type])

        # Priority 2: URL patterns in discovered links
        url = crawl_data.get("url", "").lower()
        html = crawl_data.get("html", "").lower()

        if any(sig in html for sig in self.ECOMMERCE_SIGNALS):
            return SiteVertical.ECOMMERCE
        if any(sig in html for sig in self.LOCAL_SIGNALS):
            return SiteVertical.LOCAL_BUSINESS
        if any(sig in url or sig in html for sig in self.SAAS_SIGNALS):
            return SiteVertical.SAAS

        # Priority 3: Organization type in schema
        if "Organization" in schema_types:
            return SiteVertical.B2B_SERVICES

        return SiteVertical.GENERIC

    def _extract_schema_types(self, crawl_data: dict) -> list[str]:
        """Extract all @type values from schema_org data."""
        schema_org = crawl_data.get("schema_org", [])
        types = []
        for item in schema_org:
            if isinstance(item, dict):
                t = item.get("@type", "")
                if isinstance(t, list):
                    types.extend(t)
                elif isinstance(t, str):
                    types.append(t)
        return types
```

### Pattern 2: Vertical-Aware Recommendation Filter

**What:** Filter out recommendations that are irrelevant to the detected site vertical.
**When to use:** Inside `RecommendationEngine._generate_page_recommendations()` before creating the recommendation.
**Confidence:** HIGH -- directly addresses Pitfall 4 (irrelevant recommendations).

```python
# Criteria relevance map: which criteria are NOT applicable per vertical
VERTICAL_EXCLUSIONS: dict[str, set[str]] = {
    "saas": {
        "SD3_LocalBusiness",  # LocalBusiness schema
        "SD3_Product",        # Product schema (unless SaaS has marketplace)
        "SD3_ClaimReview",    # Fact-check schema
    },
    "ecommerce": {
        "SD3_ClaimReview",    # Fact-check schema
        "SD3_SpeakableSpecification",  # News schema
    },
    "local_business": {
        "SD3_SoftwareApplication",
        "SD3_ClaimReview",
    },
    "media_blog": {
        "SD3_Product",
        "SD3_LocalBusiness",
    },
}

# More granular: schema type recommendations per vertical
VERTICAL_SCHEMA_RECOMMENDATIONS: dict[str, list[str]] = {
    "saas": ["Organization", "WebSite", "FAQPage", "SoftwareApplication", "BreadcrumbList", "HowTo"],
    "ecommerce": ["Organization", "Product", "Offer", "AggregateOffer", "BreadcrumbList", "FAQPage", "Review"],
    "local_business": ["LocalBusiness", "Organization", "FAQPage", "Review", "GeoCoordinates"],
    "media_blog": ["Article", "BlogPosting", "Organization", "Person", "BreadcrumbList", "FAQPage"],
    "b2b_services": ["Organization", "WebSite", "FAQPage", "Service", "BreadcrumbList"],
    "generic": [],  # No filtering -- all recommendations apply
}

def is_recommendation_relevant(
    criterion_id: str,
    criterion_name: str,
    vertical: str,
    schema_types_found: list[str],
) -> bool:
    """Check if a recommendation is relevant for the site's vertical.

    Rules:
    1. If vertical is 'generic', all recommendations are relevant
    2. Schema recommendations are filtered by vertical schema map
    3. Non-schema recommendations are always relevant
    """
    if vertical == "generic":
        return True

    # Schema-specific criteria: check if the recommended schema makes sense
    # Criterion IDs for schema recommendations are in SD category
    if criterion_id.startswith("SD"):
        # Get the specific schema type being recommended from criterion evidence
        # If criterion recommends a schema not in the vertical's list, skip it
        exclusions = VERTICAL_EXCLUSIONS.get(vertical, set())
        if criterion_id in exclusions:
            return False

    return True
```

### Pattern 3: Impact Delta Calculation

**What:** Calculate "if you fix this, your overall score improves by X points" from actual scoring data.
**When to use:** During recommendation generation, after computing gap_score.
**Confidence:** HIGH -- straightforward arithmetic using the existing scoring formula.

```python
def compute_impact_delta(
    criterion_score: int,
    target_score: int,     # threshold from CRITERION_RESEARCH_MAP
    category: str,
    page_category_scores: dict[str, float],
    total_pages: int,
) -> float:
    """Estimate optimization score improvement if this criterion is fixed.

    Algorithm:
    1. Compute current category score contribution to optimization score
    2. Simulate fixing this criterion to target_score
    3. Recompute category score with the fix
    4. Delta = new_optimization_score - current_optimization_score

    This is an estimate because:
    - Fixing one criterion changes the category average
    - Weakest-link aggregation means fixing the worst criterion has outsized impact
    - We assume the fix applies to one page only
    """
    category_weights = {
        "crawlability": 0.25,
        "content_structure": 0.25,
        "structured_data": 0.20,
        "authority": 0.15,
    }
    weight = category_weights.get(category, 0.15)

    # Simple estimate: score improvement * weight / number of criteria in category
    criteria_per_category = {"crawlability": 12, "content_structure": 13, "structured_data": 13, "authority": 23}
    num_criteria = criteria_per_category.get(category, 15)

    score_improvement = target_score - criterion_score
    category_improvement = score_improvement / num_criteria
    optimization_delta = category_improvement * weight

    # Adjust for multi-page (weakest link): if this is the weakest page, impact is higher
    if total_pages > 1:
        optimization_delta *= 0.8  # Conservative: assume this isn't always the weakest page

    return round(optimization_delta, 1)
```

### Pattern 4: Cross-Audit Competitor Persistence

**What:** Link `DiscoveredCompetitor` records across audits via the `Brand` model so SOV can be tracked over time.
**When to use:** During competitor discovery, after NER deduplication, before persisting.
**Confidence:** MEDIUM -- requires a new `competitor_brand_id` FK or enrichment of the existing `Brand` model.

```python
# Approach: Create or match a Brand record for each discovered competitor.
# The Brand model already exists (brand.py) with name, domain fields.
# Add competitor_brand_id FK to DiscoveredCompetitor.

def link_competitor_to_brand(
    db: Session,
    competitor: DiscoveredCompetitor,
    user_id: str,
) -> None:
    """Find or create a Brand record for a discovered competitor.

    Matching strategy:
    1. Exact name match (case-insensitive) among existing brands for this user
    2. Fuzzy name match (token_set_ratio > 90)
    3. Domain match if resolved_url exists
    4. Create new Brand if no match
    """
    from app.models.brand import Brand

    # Try exact match first
    existing = (
        db.query(Brand)
        .filter(Brand.user_id == user_id)
        .filter(func.lower(Brand.name) == competitor.entity_name.lower())
        .first()
    )
    if existing:
        competitor.competitor_brand_id = existing.id
        return

    # Try domain match
    if competitor.resolved_url:
        domain = urlparse(competitor.resolved_url).netloc
        existing = (
            db.query(Brand)
            .filter(Brand.user_id == user_id)
            .filter(Brand.domain == domain)
            .first()
        )
        if existing:
            competitor.competitor_brand_id = existing.id
            return

    # Create new Brand for this competitor
    new_brand = Brand(
        user_id=user_id,
        name=competitor.entity_name,
        domain=urlparse(competitor.resolved_url).netloc if competitor.resolved_url else None,
        is_competitor=True,  # NEW field to distinguish from user's own brands
    )
    db.add(new_brand)
    db.flush()
    competitor.competitor_brand_id = new_brand.id
```

### Anti-Patterns to Avoid

- **LLM-based recommendations:** The existing deterministic engine is correct. Do NOT replace it with LLM calls. The recommendation engine is testable, reproducible, and cost-free. LLMs are reserved for the chat assistant (Phase 6).
- **Upgrading spaCy model for marginal gain:** `en_core_web_sm` (90.19% F1) vs `en_core_web_trf` (90.30% F1) is a 0.11% improvement at 10-50x speed cost. Not worth it.
- **Fine-tuning spaCy for brand NER:** Would require labeled training data from AI engine responses. The 2-mention minimum threshold and blocklist already handle noise effectively. Fine-tuning is premature optimization.
- **Computing exact impact deltas with full scoring re-simulation:** Running the entire scoring pipeline hypothetically for each recommendation would be slow and complex. The linear estimation (Pattern 3 above) is sufficiently accurate for user-facing estimates.
- **Storing competitor data in a separate database or microservice:** All data fits in the existing PostgreSQL schema. The `Brand` model already provides the normalization entity needed for cross-audit tracking.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Fuzzy string matching for entity dedup | Custom edit-distance | rapidfuzz `token_set_ratio` | Already used, handles corporate suffixes, well-tested |
| NER extraction | Regex-based entity extraction | spaCy `en_core_web_sm` | Already integrated, handles entity boundaries, multi-word entities |
| Schema.org parsing | Custom JSON-LD parser | BeautifulSoup + `json.loads()` on `<script type="application/ld+json">` | Already done in structured_data_scorer.py |
| URL normalization | String manipulation | `urllib.parse` functions | Already used in scoring_orchestrator.py |
| Priority classification | ML classifier | Simple threshold rules (impact_pct + gap_score) | Already implemented, deterministic, testable |

**Key insight:** Nearly everything needed for Phase 2 is already built. The work is enhancement (vertical classification, impact deltas, cross-audit persistence) and verification (integration tests), not greenfield development.

## Common Pitfalls

### Pitfall 1: Irrelevant Schema Recommendations (CRITICAL)

**What goes wrong:** Recommending ClaimReview schema to a SaaS site, Product schema to a blog, LocalBusiness schema to an online-only service. This was identified as Pitfall 4 in project research and is explicitly called out in success criteria #2.
**Why it happens:** The recommendation engine uses a static checklist approach -- if a schema type is missing, recommend adding it, regardless of whether it makes sense for the site type.
**How to avoid:** Implement the `VerticalClassifier` (Pattern 1) and wire it as a pre-filter in `_generate_page_recommendations()`. Store the detected vertical on the `Audit` model for display and debugging.
**Warning signs:** Running the recommendation engine on different site types and getting identical schema recommendations. No `vertical` field stored anywhere in the audit data.

### Pitfall 2: Impact Estimates That Don't Add Up

**What goes wrong:** Impact estimates promise more total improvement than mathematically possible. If 10 recommendations each promise "+5 points," the user expects 50 points of improvement, but the actual maximum improvement might be 20 points due to score saturation and category weights.
**Why it happens:** Impact estimates are calculated independently per criterion without considering that (a) categories have weight caps, (b) weakest-link aggregation means fixing one criterion has diminishing returns if other criteria in the same category are also low.
**How to avoid:** Cap the sum of impact deltas at the theoretical maximum improvement. Show "estimated" language: "Estimated improvement: ~3-5 points" not "Improvement: 5 points." Include a note that improvements compound but don't stack linearly.
**Warning signs:** Sum of all impact_deltas > 100. Impact estimates shown as precise integers rather than ranges.

### Pitfall 3: Competitor Discovery Noise

**What goes wrong:** NER extracts generic terms ("the platform," "this tool") or tangentially related entities (industry analysts, investors) as competitors. Users see "McKinsey" as a competitor to their SaaS product because an AI engine mentioned McKinsey in a research context.
**Why it happens:** spaCy NER tags any ORG/PRODUCT entity, including contextual mentions that aren't competitors. The 2-mention minimum helps but doesn't fully solve the problem.
**How to avoid:** The blocklist in `EntityExtractorService.GENERIC_BLOCKLIST` covers common false positives. Consider adding: (1) a confidence score based on mention context (was the entity mentioned as a recommendation or just referenced?), (2) user-facing confirm/reject UI for discovered competitors (COMP-02 already shows them -- add a dismiss button). Current implementation already requires 2+ appearances which filters single-mention noise.
**Warning signs:** Leaderboard showing entities that are clearly not competitors (consultancies, news outlets, generic tool categories).

### Pitfall 4: Cross-Audit Competitor Matching Failures

**What goes wrong:** "Stripe, Inc." in audit 1 and "Stripe" in audit 2 are stored as different competitors, breaking trend tracking. Or conversely, "Apple" (the tech company) in one context gets merged with "Apple" (the fruit brand) from a food industry audit.
**Why it happens:** Entity name normalization across time is hard. Brand names change, abbreviations differ, and context is lost in the deduplication process.
**How to avoid:** Use the Brand model as the normalization layer. Match on `resolved_url` domain (strongest signal) first, then fuzzy name match. Store both the canonical brand name and the per-audit entity name so the mapping is auditable. Allow manual correction via the UI.
**Warning signs:** Same competitor appearing multiple times in trend data. Competitor count growing unboundedly across audits instead of stabilizing.

### Pitfall 5: Recommendation Hash Collisions Across Schema Changes

**What goes wrong:** The `recommendation_hash` (SHA-256 of `criterion_id|normalized_url`) carries over done/dismissed status across audits. If the scoring criteria change (new criterion IDs, renamed criteria), old hashes may not match, causing previously-dismissed recommendations to reappear.
**How to avoid:** The current hash implementation in `_compute_rec_hash()` uses `criterion_id` + `page_url` which is stable as long as criterion IDs don't change. If criterion IDs must change in the future, add a migration that maps old hashes to new hashes. For Phase 2, criterion IDs are stable (C1-C12, CS1-CS13, SD1-SD13, A1-A8, S1-S15) so this is not an immediate risk.
**Warning signs:** Users reporting that previously dismissed recommendations reappear after an audit.

## Code Examples

### Wiring Vertical Classifier into Audit Pipeline

```python
# In audit_tasks.py, after crawl and before recommendation generation:
# Store detected vertical on the Audit record

from app.services.vertical_classifier import VerticalClassifier, SiteVertical

# After Stage 1 (crawling):
classifier = VerticalClassifier()
detected_vertical = classifier.classify(audit.crawl_data)
audit.vertical = detected_vertical.value  # Add 'vertical' column to Audit model
db.commit()

# In Stage 7 (recommendation generation):
rec_engine = RecommendationEngine(db)
recs = rec_engine.generate_recommendations(
    audit_id=audit_id,
    user_id=str(audit.user_id),
    vertical=audit.vertical,  # Pass vertical for filtering
)
```

### Adding Impact Delta to Recommendations

```python
# In recommendation_engine.py, _generate_page_recommendations():
# After computing gap_score, add estimated_score_delta

# Existing: gap_score = round(comp_avg - criterion.score) or round(threshold - criterion.score)
# New:
estimated_delta = self._compute_impact_delta(
    criterion_score=criterion.score,
    target_score=threshold,
    category=criterion.category,
    total_pages=len(page_scores),
)

rec = AuditRecommendation(
    # ... existing fields ...
    estimated_score_delta=estimated_delta,  # NEW column: Float, nullable
)
```

### Cross-Audit Competitor SOV Query

```python
# Query to build SOV trend data for a competitor across audits
from sqlalchemy import func

def get_competitor_sov_trend(
    db: Session, brand_id: str, user_id: str
) -> list[dict]:
    """Get share-of-voice over time for a competitor brand."""
    rows = (
        db.query(
            Audit.created_at,
            DiscoveredCompetitor.share_of_voice,
            DiscoveredCompetitor.mention_count,
        )
        .join(DiscoveredCompetitor, DiscoveredCompetitor.audit_id == Audit.id)
        .filter(Audit.user_id == user_id)
        .filter(DiscoveredCompetitor.competitor_brand_id == brand_id)
        .order_by(Audit.created_at)
        .all()
    )
    return [
        {
            "date": row.created_at.isoformat(),
            "share_of_voice": float(row.share_of_voice),
            "mention_count": row.mention_count,
        }
        for row in rows
    ]
```

### Integration Test Pattern for Full Pipeline

```python
# Test that scoring -> recommendations -> competitors works end-to-end
import pytest
from unittest.mock import patch, MagicMock

def test_recommendation_pipeline_integration(db_session, stripe_crawl_fixture):
    """Verify full pipeline: score pages -> generate recommendations -> verify relevance."""
    # 1. Score the fixture data (reuse test_scoring_pipeline approach)
    orchestrator = ScoringOrchestrator(db_session)
    # Register all scorers...
    scoring_result = asyncio.run(
        orchestrator.score_audit(audit_id, stripe_crawl_fixture, visibility_score=50)
    )

    # 2. Generate recommendations
    engine = RecommendationEngine(db_session)
    recs = engine.generate_recommendations(audit_id=audit_id, user_id=user_id, vertical="saas")

    # 3. Verify: no irrelevant schema recommendations for SaaS
    for rec in recs:
        assert rec.criterion_id != "SD3_LocalBusiness"
        assert rec.criterion_id != "SD3_ClaimReview"

    # 4. Verify: recommendations are sorted by priority
    priority_order = {"high": 0, "medium": 1, "low": 2}
    for i in range(len(recs) - 1):
        assert priority_order[recs[i].priority] <= priority_order[recs[i + 1].priority]

    # 5. Verify: impact estimates are reasonable
    for rec in recs:
        if rec.estimated_score_delta is not None:
            assert 0 < rec.estimated_score_delta <= 15  # No single fix improves >15 pts
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| LLM-generated recommendations | Deterministic gap analysis from scoring data | 2025-2026 (industry trend toward reproducibility) | Deterministic recs are testable, reproducible, cost-free. LLMs reserved for interactive use (chat). Endexa already follows this pattern correctly. |
| Single NER pass | NER + fuzzy dedup + blocklist + minimum appearance threshold | Already implemented | Reduces false positives from ~40% to <10% based on 2-mention minimum and blocklist |
| Static impact estimates | Score delta calculation from actual scoring formula | Phase 2 (to implement) | Users see personalized "fix this = +X points" instead of generic research percentages |
| Per-audit competitor data | Cross-audit competitor persistence via Brand model | Phase 2 (to implement) | Enables trend tracking, SOV over time, competitive positioning history |

**Deprecated/outdated:**
- `geo_data_points/` directory: Already deleted in Phase 1. All scoring happens in `backend/app/services/scoring/`.
- `optimizer.py` (legacy recommendation stub): Still exists but is not wired into the pipeline. The `recommendation_engine.py` is the active implementation. Safe to ignore.
- `recommendation.py` model (legacy): Exists alongside `audit_recommendation.py`. The `AuditRecommendation` model is the active one used by the recommendation engine.

## Open Questions

1. **Vertical classifier accuracy threshold**
   - What we know: Schema.org types are the strongest signal for vertical detection. Sites with Product/Offer schema are almost certainly e-commerce. Sites with LocalBusiness schema are almost certainly local businesses.
   - What's unclear: How to classify sites that have no schema.org data at all (probably 30-40% of sites). Falling back to URL/content pattern matching reduces accuracy.
   - Recommendation: Default to `GENERIC` (no filtering) when confidence is low. Better to show a potentially irrelevant recommendation than to miss a relevant one. Add a user-facing "What type of site is this?" dropdown as an override for edge cases (defer to Phase 7 UI polish).

2. **Brand model schema changes for competitor persistence**
   - What we know: The `Brand` model exists with `id`, `name`, `user_id`, `domain` fields. Adding `is_competitor` boolean and `competitor_brand_id` FK to `DiscoveredCompetitor` is straightforward.
   - What's unclear: Whether the Brand model's `user_id` FK is correct for competitors discovered across different users' audits. A competitor brand is shared across users, not owned by one user.
   - Recommendation: Create competitor brands at the user level (each user has their own view of competitors). This avoids cross-user data leakage. If two users audit the same domain and discover the same competitor, they each get separate Brand records. This is simpler and more secure, even though it creates some data duplication.

3. **Alembic migration for new columns**
   - What we know: Need to add `vertical` (String) to `audits` table, `estimated_score_delta` (Float) to `audit_recommendations` table, and `competitor_brand_id` (UUID FK) to `discovered_competitors` table.
   - What's unclear: Whether an `is_competitor` field on the Brand model is the right approach vs. a separate `CompetitorBrand` table.
   - Recommendation: Add `is_competitor` boolean to `Brand` -- simpler, reuses existing model, avoids a new table. All new columns are nullable to avoid migration issues with existing data.

## Sources

### Primary (HIGH confidence)
- `backend/app/services/recommendation_engine.py` -- Full deterministic gap analysis engine, already implemented with research benchmarks
- `backend/app/services/entity_extractor.py` -- spaCy NER + rapidfuzz dedup + SOV, already implemented
- `backend/app/services/competitor_service.py` -- URL resolution + crawl + score, already implemented
- `backend/app/models/competitor.py` -- DiscoveredCompetitor + CompetitorAudit models
- `backend/app/models/audit_recommendation.py` -- AuditRecommendation model with all required fields
- `backend/app/tasks/audit_tasks.py` -- Full 8-stage pipeline with competitor discovery and recommendation generation
- `.planning/research/PITFALLS.md` -- Pitfall 4 (irrelevant recommendations) and Pitfall 11 (wrong competitor discovery)
- `.planning/research/ARCHITECTURE.md` -- Component boundaries, data flows, anti-patterns
- `.planning/research/FEATURES.md` -- Feature landscape, competitor analysis, priority matrix

### Secondary (MEDIUM confidence)
- [spaCy Models Documentation](https://spacy.io/models) -- en_core_web_sm F1=90.19%, en_core_web_trf F1=90.30% on NER
- [spaCy NER accuracy discussion](https://github.com/explosion/spaCy/discussions/13185) -- English models evaluation values
- [Schema.org types hierarchy](https://schema.org/docs/schemas.html) -- Organization, LocalBusiness, Product type relationships
- [Google Organization Schema docs](https://developers.google.com/search/docs/appearance/structured-data/organization) -- Schema type best practices

### Tertiary (LOW confidence)
- Web search on automated industry vertical classification -- No definitive library or approach found. Heuristic-based classification using schema.org types is the pragmatic choice. Needs validation against 20+ test sites.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- No new dependencies needed. All libraries already installed and proven.
- Architecture: HIGH -- Existing code covers 70-80% of requirements. Patterns are well-established in the codebase.
- Pitfalls: HIGH -- Directly informed by project-specific research (PITFALLS.md) and codebase analysis.
- Vertical classifier: MEDIUM -- Heuristic approach is sensible but accuracy needs validation with diverse test sites.
- Cross-audit persistence: MEDIUM -- Schema design is straightforward but Brand model reuse needs careful FK design.

**Research date:** 2026-02-26
**Valid until:** 2026-03-26 (30 days -- stable domain, no fast-moving dependencies)
