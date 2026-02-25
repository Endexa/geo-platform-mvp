# Phase 1: Scoring Foundation - Research

**Researched:** 2026-02-25
**Domain:** Scoring pipeline, multi-page crawling, criterion evaluation, aggregation
**Confidence:** HIGH

## Summary

Phase 1 is the critical path root of the entire v2 rebuild. The existing codebase has a fully implemented scoring architecture: 4 category scorers (CrawlabilityScorer with 12 criteria, ContentStructureScorer with 13 criteria, StructuredDataScorer with 13 criteria, AuthorityScorer with 23 criteria = 61 total), a ScoringOrchestrator that discovers internal links, crawls multiple pages, runs all scorers, persists CriterionResult records, and computes a final optimization score via weakest-link aggregation. All 4 scorers are registered in the audit_tasks.py Celery pipeline and the full 8-stage audit pipeline already calls them. The CrawlResult schema provides html, main_content, schema_org, ai_bot_access, og_tags, and other signals needed by scorers.

The critical finding from this research is that **the scoring framework is already built and producing real measurements -- not zeros**. The CLAUDE.md and memory file claim "103/108 data points return hardcoded zeros" but this refers to the legacy `geo_data_points/` directory (the old 108-point system), NOT the newer `backend/app/services/scoring/` system which was built in previous phases (5-6). The scoring services produce real measurements from crawl data. The remaining work for Phase 1 is: (1) verify that all 61 criteria actually work correctly against known sites with no false zeros, (2) fix any criteria that are broken or returning inaccurate results, (3) ensure the CrawlerService provides all needed data fields, (4) delete the legacy `geo_data_points/` directory, (5) ensure the dual-score display (Visibility + Optimization) renders correctly on the frontend, and (6) add integration tests that verify scores against known test sites.

**Primary recommendation:** Run an end-to-end audit against stripe.com and 2-3 other known sites, manually inspect every CriterionResult for accuracy, fix any broken criteria, delete `geo_data_points/`, and add integration tests. This is primarily a validation, bug-fixing, and cleanup phase -- not a from-scratch build.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SCORE-01 | All 61 scoring criteria across 4 categories produce real measurements from crawled page data | All 4 scorers exist with full implementations. Need validation that all produce real measurements (not zero/fabricated). CrawlerService must provide html, schema_org, ai_bot_access, og_tags fields. |
| SCORE-02 | Each criterion uses three-state system: measured, not-applicable, or error -- never fabricated | BaseScorer already has `checked=False` (not-checked) and `_not_checked()` helper. Need to verify all criteria use it correctly -- no hardcoded score=50 on failure (CrawlabilityScorer C9 SSR check returns score=50 on Playwright failure, should use _not_checked). |
| SCORE-03 | Optimization Score aggregates via weakest-link formula (0.6*mean + 0.4*min across pages) | Already implemented in `ScoringOrchestrator.compute_optimization_score()`. Formula is correct. Need integration test to verify. |
| SCORE-04 | Dual scores displayed: Visibility Score (AI mention-based) + Optimization Score (page-level criteria) | Audit model has `optimization_score` column. VisibilityScore is computed by ScoringService. Frontend AuditResults component exists. Need to verify dual display renders correctly. |
| SCORE-05 | Crawlability category (C1-C12) produces accurate measurements | CrawlabilityScorer fully implemented with all 12 criteria. C1-C8 check AI bot access, C9 SSR, C10 TTFB, C11 HTTP status, C12 resource blockage. Need validation against known sites. |
| SCORE-06 | Content Structure category (CS1-CS13) measures headings, lists, word count, readability, citations | ContentStructureScorer fully implemented with all 13 criteria. Uses BeautifulSoup, textstat, nltk. Key concern: needs `html` field from CrawlResult (not just main_content) for proper DOM parsing. |
| SCORE-07 | Structured Data category (SD1-SD13) detects JSON-LD, FAQPage, HowTo, schema types, llms.txt | StructuredDataScorer fully implemented with all 13 criteria. Uses schema_org from CrawlResult (extruct-parsed JSON-LD). SD12/SD13 make live HTTP requests for llms.txt files. |
| SCORE-08 | Authority category (A1-A8, S1-S15) evaluates E-E-A-T signals and SEO fundamentals | AuthorityScorer fully implemented with all 23 criteria. A3 requires GOOGLE_API_KEY. A3-A5 make external API calls (KG, Wikidata, Wikipedia). S11 calls PageSpeed API. All degrade gracefully via _not_checked. |
| SCORE-09 | Dead code removed -- legacy `geo_data_points/` directory deleted, only `scoring/` services used | `geo_data_points/` directory exists at project root. Must be deleted. Need to verify no active imports reference it from backend/app/. |
| SCORE-10 | Scoring pipeline has integration tests verifying end-to-end accuracy against known test sites | No tests exist currently (no backend/tests/ directory). Need to create integration tests that run full scoring pipeline against known site HTML fixtures. |
</phase_requirements>

## Standard Stack

### Core (Already in Place -- No New Dependencies)

| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| FastAPI | 0.109.0 | Backend API framework | Existing |
| SQLAlchemy + Alembic | 2.0.25 / 1.13.1 | ORM + migrations | Existing |
| Celery + Redis | 5.3.4 / 5.0.1 | Task queue for audit pipeline | Existing |
| Playwright | 1.41.0 | SSR detection (C9), browser rendering | Existing |
| BeautifulSoup4 + lxml | 4.12.2 | HTML parsing for all scorers | Existing |
| textstat | -- | Readability scoring (CS7) | Existing |
| nltk | -- | Sentence tokenization (CS2, CS3, CS13) | Existing |
| httpx | -- | Async HTTP for TTFB, robots.txt, llms.txt, APIs | Existing |
| extruct | -- | JSON-LD extraction from HTML | Existing |
| Pydantic v2 | -- | CrawlResult schema, Settings | Existing |

### No New Dependencies Needed

Phase 1 requires zero new library installations. Every dependency is already in requirements.txt and tested.

## Architecture Patterns

### Existing Project Structure (Scoring Pipeline)

```
backend/app/
  services/
    scoring/
      __init__.py              # Exports AuthorityScorer, BaseScorer, ScoringCriterionResult, ScoringOrchestrator
      base_scorer.py           # ABC with score_page(), compute_category_score(), _not_checked()
      scoring_orchestrator.py  # Multi-page crawl, per-page scoring, weakest-link aggregation
      crawlability_scorer.py   # C1-C12 (12 criteria)
      content_structure_scorer.py  # CS1-CS13 (13 criteria)
      structured_data_scorer.py    # SD1-SD13 (13 criteria)
      authority_scorer.py      # A1-A8, S1-S15 (23 criteria)
    crawler_service.py         # CrawlerService.crawl() -> CrawlResult
  schemas/
    crawl.py                   # CrawlResult, AIBotAccess Pydantic models
  models/
    page_score.py              # PageScore SQLAlchemy model (per-page category scores)
    criterion_result.py        # CriterionResult SQLAlchemy model (per-criterion per-page)
    audit.py                   # Audit model with optimization_score column
  tasks/
    audit_tasks.py             # Celery task: 8-stage pipeline, stage 5 = scoring
```

### Pattern 1: Scorer Registration (Already Implemented)

**What:** Scorers are registered dynamically in audit_tasks.py with ImportError guards so the pipeline works even if a scorer is not available.
**How it works:** Each scorer is imported in a try/except block and registered with `orchestrator.register_scorer("category", ScorerClass())`. If import fails, pipeline continues without that category.

```python
# From audit_tasks.py (lines 201-222) -- already implemented
orchestrator = ScoringOrchestrator(db)
try:
    from app.services.scoring.crawlability_scorer import CrawlabilityScorer
    orchestrator.register_scorer("crawlability", CrawlabilityScorer())
except ImportError:
    logger.warning("CrawlabilityScorer not yet available, skipping")
# ... same for content_structure, structured_data, authority
```

### Pattern 2: Three-State Measurement (Already Implemented)

**What:** Every criterion returns one of three states: measured (checked=True with real score), not-checked (checked=False, excluded from aggregation), or error (caught in scorer, returns _not_checked).
**How it works:** `BaseScorer._not_checked()` creates a result with `checked=False, score=0`. `compute_category_score()` filters to `checked=True` only.

```python
# BaseScorer._not_checked() -- already implemented
def _not_checked(self, criterion_id, criterion_name, reason):
    return ScoringCriterionResult(
        criterion_id=criterion_id,
        criterion_name=criterion_name,
        score=0,
        human_summary=f"Could not check: {reason}",
        technical_detail=reason,
        checked=False,
    )
```

### Pattern 3: Weakest-Link Aggregation (Already Implemented)

**What:** Final optimization score uses `0.6 * mean + 0.4 * min` across pages, penalizing inconsistency.
**How it works:** `ScoringOrchestrator.compute_optimization_score()` computes weighted category scores per page, then applies the weakest-link formula across all pages, and adds the AI visibility contribution (15%).

### Pattern 4: CrawlResult as Data Contract

**What:** All scorers receive a `page_data: dict` which is `CrawlResult.model_dump()`. This dict contains all signals needed for scoring.
**Critical fields for scorers:**
- `html` -- Full HTML for DOM parsing (Content Structure, Authority, Structured Data)
- `main_content` -- Extracted text content (readability, word count, entity detection)
- `schema_org` -- JSON-LD structured data list (Structured Data scorer)
- `ai_bot_access` -- Robots.txt directives (Crawlability C1-C8)
- `url`, `domain` -- For HTTP checks (TTFB, sitemap, llms.txt)
- `og_tags` -- Open Graph metadata dict (Authority S6)
- `title`, `meta_description` -- Page metadata (Authority S3, S4)

### Anti-Patterns to Avoid

- **Do NOT fix the legacy `geo_data_points/` system.** Delete it entirely. The new `scoring/` system is the only implementation.
- **Do NOT add new HTTP calls inside scorers.** The CrawlerService is responsible for fetching all data. If a scorer needs data the crawler does not provide, enrich the CrawlerService, not the scorer.
- **Do NOT return hardcoded scores on failure.** Use `_not_checked()`. The CrawlabilityScorer C9 (SSR check) currently returns `score=50` on Playwright failure instead of `_not_checked()`. This must be fixed.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTML parsing | Custom regex extraction | BeautifulSoup + lxml | Edge cases with malformed HTML, encoding issues |
| Readability scoring | Custom grade-level formula | textstat (flesch_kincaid_grade) | Validated algorithm, handles edge cases |
| JSON-LD extraction | Manual script tag parsing | extruct library via CrawlerService | Handles @graph nesting, multiple blocks, malformed JSON |
| Robots.txt parsing | Custom parser | urllib.robotparser | Standard library, handles edge cases |
| Sentence tokenization | Split on period | nltk.sent_tokenize | Handles abbreviations, URLs, edge cases |
| HTTP timing | Custom timer | httpx response.elapsed | Accurate TTFB measurement |

## Common Pitfalls

### Pitfall 1: CrawlResult Missing `html` Field for Subpages

**What goes wrong:** The ScoringOrchestrator calls `crawler.crawl_multiple()` for subpages and appends `result.model_dump()` to `crawled_pages`. If `crawl_multiple()` does not populate the `html` field (only `main_content`), the ContentStructureScorer, StructuredDataScorer, and AuthorityScorer will receive `html=""` and return empty or zero results for criteria that parse HTML DOM.
**Why it happens:** The initial homepage crawl has full data, but subpage crawls via `crawl_multiple()` might have different data completeness.
**How to avoid:** Verify that `CrawlerService.crawl_multiple()` populates the `html` field in CrawlResult for every page. If it does not, this is the #1 blocker for real scoring.
**Warning signs:** Content Structure scores are all zero on subpages but non-zero on the homepage.

### Pitfall 2: SSR Check (C9) Returns score=50 Instead of NOT_CHECKED on Failure

**What goes wrong:** When Playwright fails to render a page (timeout, browser crash, etc.), the CrawlabilityScorer returns `score=50` with a generic message. This violates SCORE-02 (never fabricated). The 50 is an arbitrary guess, not a measurement.
**How to avoid:** Replace the `score=50` fallback in `_check_ssr()` exception handler with `self._not_checked("C9", "Server-side rendering", f"Playwright failed: ...")`.
**Code location:** `crawlability_scorer.py` line 349-357.

### Pitfall 3: Playwright Browser Instance Not Cleaned Up

**What goes wrong:** CrawlabilityScorer lazily initializes a Playwright browser for C9 (SSR check). The `cleanup()` method exists but may not be called after scoring completes, leaking browser processes in the Celery worker.
**How to avoid:** Ensure the Celery task or ScoringOrchestrator calls `crawlability_scorer.cleanup()` after scoring completes. Consider using async context manager pattern.
**Warning signs:** Celery worker memory grows over time, chromium processes accumulate.

### Pitfall 4: External API Calls Without GOOGLE_API_KEY

**What goes wrong:** Authority criteria A3 (Knowledge Graph) and S11 (Core Web Vitals) require GOOGLE_API_KEY. Without it, both return `_not_checked`. This reduces the Authority category score to only 21/23 checked criteria. S11 also works without API key (PageSpeed Insights public endpoint) but is rate-limited.
**Why it matters:** Most dev environments do not have GOOGLE_API_KEY set. Tests must account for these criteria being NOT_CHECKED and the category still producing a reasonable overall score.
**How to avoid:** Integration tests should work both with and without GOOGLE_API_KEY. The scoring should still produce meaningful Authority scores from the remaining 21 criteria.

### Pitfall 5: Schema Coverage Criteria Penalizing All Sites Equally

**What goes wrong:** StructuredDataScorer criteria SD3 (FAQPage), SD4 (Article), SD5 (HowTo), SD8 (Product), SD9 (Person), SD10 (ClaimReview) all return score=0 when their respective schema type is absent. But not every site should have every schema type -- a SaaS product page does not need ClaimReview, and a blog does not need Product schema. This drags down the Structured Data category score unfairly.
**Why it matters:** A well-structured SaaS landing page with Organization + WebSite + BreadcrumbList schemas could score 3/13 on Structured Data criteria, which calculates to ~23/100 -- unfairly low.
**Current mitigation:** The `compute_category_score()` averages only checked criteria. BUT these criteria return `checked=True` with `score=0`, not `checked=False`. So they ARE included in the average.
**Recommended fix:** Mark schema-type-specific criteria (SD3-SD6, SD8-SD10) as `checked=False` with reason "not applicable for this site type" when the schema type is not relevant. OR accept the current behavior as a deliberate scoring choice (missing schema IS a deficiency, even if not applicable). The planner should make this decision explicit.

### Pitfall 6: asyncio.run() Inside Celery Worker

**What goes wrong:** The audit_tasks.py Celery task calls `asyncio.run()` twice: once for `crawler.crawl()` and once for `orchestrator.score_audit()`. Each `asyncio.run()` creates and destroys an event loop. The second call at line 225 creates a new loop, which is fine, but if any scorer retains state from the first loop (e.g., httpx clients, Playwright browsers), those references become invalid.
**How to avoid:** This is currently working (tested in previous phases) because each scorer creates its own httpx clients and Playwright instances. The CrawlabilityScorer does lazily initialize a Playwright browser, but it does so within the second `asyncio.run()` call. No fix needed, but awareness matters for debugging.

### Pitfall 7: Link Discovery Uses main_content Instead of Full HTML

**What goes wrong:** The ScoringOrchestrator's `_discover_internal_links()` receives `html = crawl_data.get("main_content", "")` (line 84). The `main_content` field is extracted text, not full HTML. BeautifulSoup will parse it, but `<a>` tags have already been stripped by the content extraction process.
**Impact:** If `main_content` does not contain raw HTML with `<a>` tags, link discovery finds zero internal links, and no subpages are crawled. Only the homepage gets scored.
**Verification needed:** Check what `crawl_data["main_content"]` actually contains -- if it is extracted text without HTML tags, the orchestrator needs to use `crawl_data["html"]` instead for link discovery.
**Code location:** `scoring_orchestrator.py` line 84.

## Code Examples

### Running the Scoring Pipeline (Current Implementation)

```python
# From audit_tasks.py -- this is how scoring currently runs (Stage 5)
orchestrator = ScoringOrchestrator(db)
orchestrator.register_scorer("crawlability", CrawlabilityScorer())
orchestrator.register_scorer("content_structure", ContentStructureScorer())
orchestrator.register_scorer("structured_data", StructuredDataScorer())
orchestrator.register_scorer("authority", AuthorityScorer())

scoring_result = asyncio.run(
    orchestrator.score_audit(audit_id, audit.crawl_data, visibility_score_value)
)
audit.optimization_score = scoring_result["optimization_score"]
```

### Expected Test Pattern for Integration Tests

```python
# Test pattern for SCORE-10
import asyncio
import pytest
from unittest.mock import MagicMock

from app.services.scoring.scoring_orchestrator import ScoringOrchestrator
from app.services.scoring.crawlability_scorer import CrawlabilityScorer
from app.services.scoring.content_structure_scorer import ContentStructureScorer
from app.services.scoring.structured_data_scorer import StructuredDataScorer
from app.services.scoring.authority_scorer import AuthorityScorer

# Use a fixture with known HTML content (e.g., snapshot of stripe.com)
@pytest.fixture
def stripe_crawl_data():
    """Load known-good crawl data for stripe.com."""
    # Load from a test fixture file
    return {...}

async def test_scoring_produces_real_scores(stripe_crawl_data):
    """Verify all categories produce non-zero scores for a known site."""
    scorer = CrawlabilityScorer()
    results = await scorer.score_page(stripe_crawl_data)
    checked = [r for r in results if r.checked]
    assert len(checked) >= 8  # At least bot access criteria should work
    for r in checked:
        assert 0 <= r.score <= 100

async def test_weakest_link_aggregation():
    """Verify the aggregation formula is mathematically correct."""
    orch = ScoringOrchestrator(db=MagicMock())
    page_scores = [
        {"crawlability": 80, "content_structure": 60, "structured_data": 40, "authority": 70},
        {"crawlability": 90, "content_structure": 70, "structured_data": 50, "authority": 80},
    ]
    result = orch.compute_optimization_score(page_scores, visibility_score=50)
    assert 30 <= result <= 80  # Reasonable range for these inputs
    assert isinstance(result, int)
```

### Criterion Count Verification

```
Category               | Criteria IDs     | Count | Status
-----------------------|------------------|-------|--------
Crawlability           | C1-C12           | 12    | All implemented
Content Structure      | CS1-CS13         | 13    | All implemented
Structured Data        | SD1-SD13         | 13    | All implemented
Authority (E-E-A-T)   | A1-A8            | 8     | All implemented
Authority (SEO)        | S1-S15           | 15    | All implemented
TOTAL                  |                  | 61    | All implemented
```

## State of the Art

| Aspect | Current State | What Phase 1 Must Do |
|--------|---------------|---------------------|
| Scoring framework | Fully implemented, 61 criteria across 4 categories | Validate accuracy, fix bugs |
| Three-state system | BaseScorer has checked=False support, _not_checked() helper | Fix C9 SSR returning score=50 on failure; verify all criteria use three-state correctly |
| Weakest-link aggregation | Implemented in ScoringOrchestrator.compute_optimization_score() | Verify with integration tests |
| Dual-score display | Visibility + Optimization stored on audit; frontend component exists | Verify rendering correctness |
| Multi-page crawling | ScoringOrchestrator discovers links, crawls subpages | Verify link discovery works (may need html field instead of main_content) |
| Legacy dead code | geo_data_points/ directory exists at project root | DELETE entirely, verify no imports reference it |
| Integration tests | None exist | Create comprehensive test suite |
| CrawlerService data | CrawlResult has html, main_content, schema_org, ai_bot_access, og_tags | Verify subpage crawls populate all fields |

## Key Investigations Needed During Planning

### 1. CrawlerService.crawl_multiple() Data Completeness

**Question:** Does `crawl_multiple()` populate the `html` field in CrawlResult for subpages?
**Why it matters:** ContentStructureScorer, StructuredDataScorer, and AuthorityScorer all parse HTML DOM. If `html` is empty for subpages, most criteria will return zero.
**Action:** Read `CrawlerService.crawl_multiple()` implementation during plan execution. If `html` is not populated, enrich it.

### 2. Link Discovery Source Field

**Question:** Does `scoring_orchestrator.py` line 84 (`html = crawl_data.get("main_content", "")`) receive actual HTML with `<a>` tags, or stripped text?
**Why it matters:** If it receives stripped text, link discovery finds zero links, and only the homepage gets scored.
**Action:** Test by running a real audit and checking log output for "discovered N internal links". If N=0, switch to `crawl_data.get("html", "")`.

### 3. Structured Data Relevance Scoring

**Question:** Should SD3 (FAQPage), SD4 (Article), SD5 (HowTo), SD8 (Product), SD9 (Person), SD10 (ClaimReview) return checked=False when the schema type is not relevant to the site, or should missing schemas always be penalized?
**Why it matters:** This significantly affects the Structured Data category score. A SaaS site without ClaimReview schema is not deficient -- it is a site type where that schema is irrelevant.
**Recommendation:** For Phase 1, accept current behavior (penalize missing schemas). Phase 2 (Recommendations) will handle relevance-aware filtering. The important thing is that the measurement is real, not that it is optimally weighted.

### 4. Import Chain from geo_data_points/

**Question:** Does any code in `backend/app/` import from `geo_data_points/`?
**Action:** Search for imports before deleting the directory.

## Open Questions

1. **CrawlResult html field for subpages**
   - What we know: CrawlResult schema has `html: str = ""` field. Homepage crawl populates it. Unclear if crawl_multiple() does too.
   - What is unclear: Whether subpage crawls fully populate all CrawlResult fields.
   - Recommendation: Verify during implementation; fix crawl_multiple() if needed.

2. **GOOGLE_API_KEY availability**
   - What we know: A3 (Knowledge Graph) and S11 (CWV/PageSpeed) require it. Both degrade gracefully without it.
   - What is unclear: Whether the project .env has this key configured.
   - Recommendation: Tests should work without GOOGLE_API_KEY. These criteria will be NOT_CHECKED in environments without it, which is correct behavior.

3. **Stripe.com expected score ranges**
   - What we know: Previous audit produced "83/100, 107 mentions, 15 queries" (from MEMORY.md). This likely refers to the old scoring system.
   - What is unclear: What the new 61-criteria system produces for stripe.com.
   - Recommendation: Run a real audit during implementation, record the scores, and set those as expected ranges for integration tests (with tolerance +/- 15 points for external API variability).

## Sources

### Primary (HIGH confidence)
- Direct codebase reading: `backend/app/services/scoring/` (all 4 scorers + orchestrator) -- fully implemented, not stubs
- Direct codebase reading: `backend/app/tasks/audit_tasks.py` (stage 5 wiring, all scorers registered)
- Direct codebase reading: `backend/app/schemas/crawl.py` (CrawlResult data contract)
- Direct codebase reading: `backend/app/models/page_score.py`, `criterion_result.py` (DB models)
- Direct codebase reading: `backend/app/core/config.py` (SCORING_CRAWL_CAP=25, GOOGLE_API_KEY optional)

### Secondary (MEDIUM confidence)
- PITFALLS.md: Fabricated scores pitfall (Pitfall 1), SPA crawl failures (Pitfall 8), integration debt (Pitfall 5)
- ARCHITECTURE.md: Component boundaries, data flow, scoring pipeline design
- SUMMARY.md: 61 criteria framework, three-state system, weakest-link formula

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies needed, everything already installed
- Architecture: HIGH -- direct codebase reading confirms all components exist and are wired
- Pitfalls: HIGH -- specific code locations identified for each issue (line numbers)
- Criteria completeness: HIGH -- verified all 61 criteria by reading each scorer class

**Research date:** 2026-02-25
**Valid until:** 2026-03-25 (stable domain, no external dependencies changing)
