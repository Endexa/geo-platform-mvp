# Phase 6: Site AI-Readiness Scoring - Research

**Researched:** 2026-02-22
**Domain:** Page-level SEO+GEO scoring engine with 53 research-backed criteria
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Score ALL crawled pages, not just the homepage -- AI engines cite individual content pages, not homepages
- Default crawl cap of 25 pages per audit -- small sites get scored fully, large sites get the most important pages
- Page selection heuristic: homepage always included, remaining pages selected by internal link count (most linked = most important)
- Be transparent in the UI about which pages were scored and which were discovered but not scored
- Weakest link model: the lowest-scoring page pulls the overall Optimization Score down disproportionately
- Strict/realistic scoring -- most sites should score 30-60, only well-optimized sites hit 80+
- Mixed scoring mode: binary (0 or 100) for yes/no criteria, gradient (0-100) for spectrum criteria
- Friendly summary by default with expandable technical details
- Each criterion result includes both a human-readable explanation and the raw evidence
- Use free alternatives for backlink criteria (S9, S10) -- do NOT require paid APIs (Ahrefs, Moz)
- All 53 criteria should be scorable -- use free APIs where external data is needed (PageSpeed Insights, Knowledge Graph, Wikimedia)
- If a criterion truly can't be checked, exclude from score calculation and show "Not checked" (don't score as 0)

### Claude's Discretion
- Exact weakest-link formula (how much the lowest page drags down the average)
- Binary vs gradient classification for each of the 53 criteria
- Internal link count heuristic for page importance ranking
- Which free backlink data source to use (based on research findings)
- Score display visualization (gauges, bars, colors) -- whatever works best for the data
- Loading/progress UX during scoring stage
- Error handling for external API failures (PageSpeed, Knowledge Graph, etc.)

### Deferred Ideas (OUT OF SCOPE)
- Premium tier with higher/unlimited page cap -- future monetization phase
- Page selection UI (let users pick which discovered routes to score) -- future UX enhancement
- Benchmarked scoring with percentiles ("better than 60% of sites") -- requires audit history data (Phase 9)
- Full backlink integration via paid API (Ahrefs/Moz) -- when there's revenue to justify the cost
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| READY-01 | Score crawlability per page (SSR detection, AI bot access via robots.txt) | Crawlability Scorer: 12 criteria. SSR via Playwright JS-on vs JS-off comparison. Robots.txt parsing for 8+ AI bots already in CrawlerService. TTFB via httpx response timing. |
| READY-02 | Score content structure per page (answer-first, headings, paragraphs, data density, FAQ) | Content Structure Scorer: 13 criteria. textstat for readability, regex/BeautifulSoup for heading analysis, NLP heuristics for answer-first and statistics detection. |
| READY-03 | Score structured data quality (schema.org types, tiers, JSON-LD validation, FAQPage, llms.txt) | Structured Data Scorer: 13 criteria. extruct already extracts JSON-LD. Tier classification from research (Foundation/Content/Supplementary). Completeness checks per schema type. |
| READY-04 | Score authority and SEO signals (E-E-A-T, llms.txt, entity signals, SEO fundamentals) | Authority Scorer: 15 criteria. Google PageSpeed Insights API (free) for CWV. Google Knowledge Graph API (free) for entity lookup. Wikidata API (free) for QID. Proxy signals for backlinks. |
| READY-05 | Produce Optimization Score (0-100) using weighted formula alongside Visibility Score | Scoring orchestrator computes weighted sum: Crawlability 25% + Content Structure 25% + Schema 20% + Authority 15% + AI Visibility 15%. Weakest-link aggregation across pages. |
| READY-06 | Page-level breakdown with per-factor drill-down | New DB models (PageScore, CriterionResult) storing per-page, per-criterion scores. Frontend drill-down UI extending existing AuditResults pattern. |
</phase_requirements>

## Summary

Phase 6 adds a scoring engine with 53 research-backed criteria to the existing audit pipeline. The engine runs as a new SCORING stage in the Celery pipeline (after ANALYZING), scoring each of up to 25 crawled pages against criteria across four categories: Crawlability (12), Content Structure (13), Structured Data (13), and Authority/SEO (15). The existing CrawlerService currently crawls a single page; it must be extended to discover and crawl multiple pages. Each criterion produces a 0-100 score with human-readable feedback. Category scores aggregate to an Optimization Score using research-backed weights, displayed alongside the existing Visibility Score.

The primary technical challenges are: (1) extending the single-page crawl to multi-page with internal link discovery, (2) SSR detection requiring Playwright headless rendering alongside httpx for JS-off baseline, (3) calling three external free APIs (Google PageSpeed Insights, Google Knowledge Graph, Wikidata) with proper error handling and rate limiting, and (4) implementing proxy-based backlink estimation since no free backlink API provides reliable data. The scoring services themselves are pure computation on already-crawled HTML data, which is the simpler part.

**Primary recommendation:** Build four independent scoring services (one per category) sharing a common `BaseScorer` interface, orchestrated by a `ScoringOrchestrator` that manages multi-page crawling, parallel scoring, and weighted aggregation. Store results in `page_scores` and `criterion_results` tables. Extend the Celery pipeline with a SCORING status stage.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| textstat | 0.7.3 | Readability scoring (Flesch-Kincaid) | Already in requirements.txt, used for readability analysis |
| beautifulsoup4 | 4.12.2 | HTML parsing for content structure analysis | Already in requirements.txt, used by CrawlerService |
| extruct | >=0.17.0 | JSON-LD/schema.org extraction | Already in requirements.txt, used by CrawlerService |
| httpx | 0.26.0 | HTTP client for page fetching and external APIs | Already in requirements.txt, async support |
| playwright | 1.41.0 | Headless browser for SSR detection (JS rendering) | Already in requirements.txt, needed for JS-on rendering |
| lxml | 5.1.0 | Fast HTML parsing | Already in requirements.txt |
| re (stdlib) | - | Regex for pattern detection (statistics, dates, etc.) | Standard library |
| json (stdlib) | - | JSON-LD parsing and validation | Standard library |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| nltk | (add to requirements) | Sentence tokenization for paragraph/sentence analysis | Content Structure scorer needs sentence boundaries |
| rapidfuzz | >=3.14.0 | Fuzzy text matching | Already in requirements.txt, may help with entity matching |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Playwright for SSR | requests-html | Playwright is already installed and more reliable for JS rendering |
| Manual JSON-LD validation | pyld | pyld adds dependency for a small validation task; manual validation of key fields is sufficient |
| spaCy for NER | regex-based entity detection | spaCy adds ~500MB model download; regex + heuristics sufficient for Phase 6 criteria |
| Common Crawl for backlinks | Internal link analysis proxy | Common Crawl requires downloading/querying massive datasets; internal link analysis is a viable proxy signal |

**Installation:**
```bash
# nltk is the only new dependency needed (if not already installed)
pip install nltk
# Download punkt_tab tokenizer (lightweight, ~2MB)
python -c "import nltk; nltk.download('punkt_tab')"
```

## Architecture Patterns

### Recommended Project Structure
```
backend/app/services/scoring/
├── __init__.py               # Exports all scorers + orchestrator
├── base_scorer.py            # BaseScorer ABC with common interface
├── scoring_orchestrator.py   # Multi-page crawl + scoring coordination
├── crawlability_scorer.py    # 12 criteria (C1-C12)
├── content_structure_scorer.py  # 13 criteria (CS1-CS13)
├── structured_data_scorer.py    # 13 criteria (SD1-SD13)
└── authority_scorer.py          # 15 criteria (A1-A8, S1-S15)
```

### Pattern 1: BaseScorer Interface
**What:** Abstract base class that all four category scorers inherit from.
**When to use:** Every scoring category follows the same contract.
**Example:**
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class CriterionResult:
    """Result of scoring a single criterion."""
    criterion_id: str          # e.g., "C1", "CS3", "SD7"
    criterion_name: str        # e.g., "GPTBot access"
    score: int                 # 0-100
    max_score: int             # 100 (for weighted calculations)
    is_binary: bool            # True = 0 or 100 only
    human_summary: str         # Friendly explanation
    technical_detail: str      # Raw evidence
    evidence: Optional[dict]   # Machine-readable evidence (for drill-down)
    checked: bool              # False = could not check, excluded from scoring


class BaseScorer(ABC):
    """Base class for all scoring category services."""

    @abstractmethod
    async def score_page(self, page_data: dict) -> list[CriterionResult]:
        """Score a single page against all criteria in this category.

        Args:
            page_data: Dict with crawled page data (HTML, headers, metadata).

        Returns:
            List of CriterionResult for each criterion in this category.
        """
        ...

    def compute_category_score(self, results: list[CriterionResult]) -> float:
        """Compute weighted average of checked criteria (0-100)."""
        checked = [r for r in results if r.checked]
        if not checked:
            return 0.0
        return sum(r.score for r in checked) / len(checked)
```

### Pattern 2: Scoring Orchestrator
**What:** Coordinates multi-page crawling, parallel scoring, and aggregation.
**When to use:** Called from the Celery pipeline as the SCORING stage.
**Example:**
```python
class ScoringOrchestrator:
    """Orchestrates multi-page scoring for an audit."""

    CATEGORY_WEIGHTS = {
        "crawlability": 0.25,
        "content_structure": 0.25,
        "structured_data": 0.20,
        "authority": 0.15,
        "ai_visibility": 0.15,  # From existing VisibilityScore
    }

    CRAWL_CAP = 25  # Default max pages per audit (configurable)

    async def score_audit(self, audit_id: str, crawl_data: dict, db: Session) -> dict:
        """Run full scoring pipeline for an audit.

        1. Discover internal links from initial crawl
        2. Select top pages by link count (up to CRAWL_CAP)
        3. Crawl selected pages
        4. Score each page with all 4 scorers
        5. Aggregate to per-page, per-category, and overall scores
        """
        ...

    def compute_optimization_score(
        self, page_scores: list[dict], visibility_score: int
    ) -> int:
        """Compute the overall Optimization Score using weakest-link model.

        Steps:
        1. For each page, compute weighted category score
        2. Aggregate across pages using weakest-link formula
        3. Include AI Visibility score at 15% weight
        """
        ...

    def weakest_link_aggregate(self, page_scores: list[float]) -> float:
        """Weakest-link aggregation: weighted average pulled toward minimum.

        Formula: 0.6 * average + 0.4 * minimum

        This means the worst page contributes 40% to the final score,
        encouraging fixing the weakest pages first.
        """
        if not page_scores:
            return 0.0
        avg = sum(page_scores) / len(page_scores)
        minimum = min(page_scores)
        return 0.6 * avg + 0.4 * minimum
```

### Pattern 3: Multi-Page Crawl Extension
**What:** Extend existing CrawlerService to discover and crawl multiple pages.
**When to use:** Phase 6 requires scoring all crawled pages, not just the initial URL.
**Example:**
```python
async def discover_internal_links(self, soup: BeautifulSoup, base_url: str) -> list[dict]:
    """Extract internal links with their anchor text and count occurrences.

    Returns list of {url, anchor_text, link_count} sorted by link_count desc.
    Used for page importance ranking (most linked = most important).
    """
    ...

async def crawl_multiple(self, start_url: str, max_pages: int = 25) -> list[CrawlResult]:
    """Crawl multiple pages starting from start_url.

    1. Crawl start_url (homepage always included)
    2. Discover internal links from all crawled pages
    3. Rank by internal link count
    4. Crawl top pages up to max_pages cap

    Returns list of CrawlResult, one per crawled page.
    """
    ...
```

### Pattern 4: External API Calls with Graceful Degradation
**What:** Free external APIs (PageSpeed, Knowledge Graph, Wikidata) with failure handling.
**When to use:** Authority scorer criteria that need external data.
**Example:**
```python
async def check_pagespeed(self, url: str) -> Optional[dict]:
    """Call Google PageSpeed Insights API for Core Web Vitals.

    Free tier: 25,000/day, 240/minute.
    Returns None on failure (criterion marked as 'Not checked').
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://www.googleapis.com/pagespeedonline/v5/runPagespeed",
                params={"url": url, "category": "performance", "strategy": "mobile"},
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        logger.warning("PageSpeed API failed for %s", url)
    return None  # Criterion excluded from score, shown as "Not checked"
```

### Anti-Patterns to Avoid
- **Scoring stubs that return 0:** User explicitly wants all 53 criteria functional. Each criterion must have real implementation logic.
- **Blocking the pipeline on external API failures:** External APIs (PageSpeed, Knowledge Graph, Wikidata) must fail gracefully. If an API is down, exclude the criterion from the score calculation and show "Not checked" -- do NOT score as 0.
- **Single-threaded page crawling:** Multiple pages should be crawled concurrently (with asyncio semaphores to respect rate limits).
- **Storing only aggregate scores:** Per-criterion results must be stored in the DB for drill-down display. This is explicitly required by READY-06.
- **Hard-coding the crawl cap:** Make it configurable via Settings for future premium tiers.
- **Treating all criteria equally:** Binary criteria (C1-C8, S1) and gradient criteria (CS1-CS13) have different scoring profiles. Respect the binary/gradient distinction.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Readability scoring | Custom Flesch-Kincaid formula | `textstat.flesch_kincaid_grade()` | Already in requirements, handles edge cases |
| HTML heading extraction | Custom tag parsing | `BeautifulSoup.find_all('h1')` etc. | Already used by CrawlerService |
| JSON-LD extraction | Custom script tag parsing | `extruct.extract()` with `json-ld` syntax | Already in requirements, handles malformed JSON-LD |
| Sentence tokenization | Regex splitting on `.` | `nltk.sent_tokenize()` | Handles abbreviations, quotes, edge cases |
| Robots.txt parsing | Custom parser | `urllib.robotparser.RobotFileParser` | Already used by CrawlerService |
| JS rendering | Custom browser automation | `playwright` async API | Already in requirements, handles timeouts and crashes |
| Core Web Vitals | Custom performance measurement | Google PageSpeed Insights API (free) | Standardized, trusted, free |
| Entity disambiguation | Custom web scraping | Google Knowledge Graph API / Wikidata API | Authoritative data, free APIs |

**Key insight:** The crawler, extruct, textstat, and robots.txt parsing are all already in the codebase. The scoring services are primarily *analysis* of already-extracted data, not new data acquisition (except for the 3 external APIs and multi-page crawling).

## Common Pitfalls

### Pitfall 1: SSR Detection False Positives
**What goes wrong:** Comparing JS-rendered vs no-JS content produces false matches when pages use progressive enhancement (content exists in HTML but JS adds interactive elements).
**Why it happens:** Simple text comparison flags any JS-added content as "JS-only" even if the core content is in the HTML source.
**How to avoid:** Compare *main content* text (using the same `_extract_main_content` cascade as CrawlerService), not the full HTML. A content difference ratio below 20% means the page is effectively SSR-friendly. Only flag pages where the content difference exceeds a threshold (e.g., >50% of main content is JS-only).
**Warning signs:** Sites like Next.js/Nuxt with SSR getting flagged as CSR-only.

### Pitfall 2: External API Rate Limits During Batch Scoring
**What goes wrong:** Scoring 25 pages means 25 PageSpeed API calls, 25 Knowledge Graph calls, etc. Hitting rate limits causes cascading failures.
**Why it happens:** Scoring all pages in parallel without throttling.
**How to avoid:** Use asyncio semaphores (max 3-5 concurrent external API calls). The PageSpeed API allows 240/min, but each call takes 10-30 seconds, so concurrency is the bottleneck. Cache results per domain (Knowledge Graph, Wikidata queries are per-domain, not per-page).
**Warning signs:** HTTP 429 responses from Google APIs.

### Pitfall 3: Overly Generous Scoring
**What goes wrong:** Sites score 70-80 by default, contradicting the user's requirement for strict scoring (most sites should score 30-60).
**Why it happens:** Treating binary criteria (which most sites pass) equally with gradient criteria (where most sites score poorly).
**How to avoid:** Binary criteria should be weighted lower in the category average. The gradient criteria (content quality, schema completeness, authority signals) are where most sites fall short. Calibrate thresholds against known sites: stripe.com should score ~83 (already established as baseline), a typical small business site should score 30-50.
**Warning signs:** All test sites scoring above 60.

### Pitfall 4: Crawl Scope Explosion
**What goes wrong:** Internal link discovery finds hundreds of URLs on large sites, causing timeouts and memory issues.
**Why it happens:** No deduplication, no cap enforcement, following pagination/filter links.
**How to avoid:** Enforce the 25-page cap strictly. Deduplicate URLs (normalize trailing slashes, fragments, query params). Skip obvious non-content URLs (pagination, filters, login, assets). BFS from homepage with the link-count heuristic for priority.
**Warning signs:** Crawl phase taking >60 seconds, memory usage spiking.

### Pitfall 5: Playwright Startup Overhead in Celery
**What goes wrong:** Launching a Playwright browser for SSR detection adds 2-5 seconds per page, multiplied by 25 pages = 50-125 seconds just for SSR checks.
**Why it happens:** Each SSR check launches a new browser context.
**How to avoid:** Launch ONE Playwright browser instance for the entire scoring pass. Create a new page (tab) per URL check, not a new browser. Reuse the browser across all 25 pages. Consider running SSR checks in batches of 5 with asyncio.gather.
**Warning signs:** Scoring stage taking >5 minutes.

### Pitfall 6: asyncio.run Inside Celery
**What goes wrong:** The existing pipeline uses `asyncio.run()` for the CrawlerService. Nesting multiple `asyncio.run()` calls or mixing with existing event loops causes "cannot run nested event loop" errors.
**Why it happens:** Celery workers may already have an event loop (from the 03-01 thread-local pattern).
**How to avoid:** Follow the existing pattern from Phase 3: use `asyncio.run()` at the top level of the Celery task for the scoring stage, or use the existing thread-pool pattern. The scoring services should be `async` internally and called from a single `asyncio.run()` in the Celery task.
**Warning signs:** RuntimeError about nested event loops.

### Pitfall 7: Database Schema Bloat
**What goes wrong:** Storing 53 criterion results per page x 25 pages = 1,325 rows per audit in criterion_results. With frequent audits, this grows fast.
**Why it happens:** Each criterion result is a separate row.
**How to avoid:** This is actually fine for the MVP. 1,325 rows per audit is tiny for PostgreSQL. Use JSONB for the `evidence` field to avoid schema changes when adding criteria later. Add an index on `page_score_id` for efficient drill-down queries.
**Warning signs:** Slow audit detail queries (add appropriate indexes).

## Code Examples

### Multi-Page Crawl with Internal Link Discovery
```python
# Source: Extension of existing CrawlerService pattern
from collections import Counter
from urllib.parse import urljoin, urlparse

async def discover_internal_links(
    self, html: str, base_url: str, domain: str
) -> list[tuple[str, int]]:
    """Extract internal links and count occurrences.

    Returns: [(url, link_count), ...] sorted by count descending.
    """
    soup = BeautifulSoup(html, "lxml")
    link_counter: Counter[str] = Counter()

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        absolute_url = urljoin(base_url, href)
        parsed = urlparse(absolute_url)

        # Same domain only
        if parsed.netloc != domain:
            continue
        # Strip fragments and normalize
        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if clean_url.endswith("/"):
            clean_url = clean_url.rstrip("/")
        # Skip non-content URLs
        if any(skip in parsed.path.lower() for skip in [
            "/login", "/signup", "/admin", "/api/", "/assets/",
            "/static/", ".pdf", ".jpg", ".png", ".css", ".js"
        ]):
            continue
        link_counter[clean_url] += 1

    return link_counter.most_common()
```

### SSR Detection with Playwright
```python
# Source: Based on Playwright async API docs
from playwright.async_api import async_playwright

async def detect_ssr(self, url: str, no_js_content: str) -> CriterionResult:
    """Compare content with and without JavaScript execution.

    Args:
        url: Page URL to render with JS.
        no_js_content: Main content extracted by httpx (no JS).

    Returns:
        CriterionResult with content diff ratio.
    """
    js_content = ""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, wait_until="networkidle", timeout=15000)
            # Extract main content the same way as CrawlerService
            js_content = await page.evaluate("""
                () => {
                    const main = document.querySelector('main')
                        || document.querySelector('article')
                        || document.querySelector('body');
                    return main ? main.innerText : '';
                }
            """)
            await browser.close()
    except Exception as e:
        return CriterionResult(
            criterion_id="C9", criterion_name="SSR Detection",
            score=50, max_score=100, is_binary=False,
            human_summary="Could not render page with JavaScript -- score uncertain",
            technical_detail=f"Playwright error: {str(e)[:200]}",
            evidence={"error": str(e)[:200]}, checked=True,
        )

    # Calculate content overlap
    no_js_words = set(no_js_content.lower().split())
    js_words = set(js_content.lower().split())

    if not js_words:
        return CriterionResult(...)  # No JS content = good SSR

    overlap = len(no_js_words & js_words) / len(js_words) if js_words else 1.0
    score = min(100, int(overlap * 100))

    return CriterionResult(
        criterion_id="C9", criterion_name="SSR Detection",
        score=score, max_score=100, is_binary=False,
        human_summary=f"{'Excellent' if score >= 80 else 'Poor'} server-side rendering: "
                      f"{score}% of content available without JavaScript",
        technical_detail=f"JS-rendered words: {len(js_words)}, "
                        f"No-JS words: {len(no_js_words)}, "
                        f"Overlap: {overlap:.1%}",
        evidence={"overlap_ratio": overlap, "js_word_count": len(js_words),
                  "no_js_word_count": len(no_js_words)},
        checked=True,
    )
```

### Content Structure Analysis (Answer-First Detection)
```python
# Source: Based on research findings about answer-first content structure
import re
import nltk

def detect_answer_first_format(heading_text: str, following_text: str) -> CriterionResult:
    """Check if content under headings follows answer-first pattern.

    Research: Answer-first format yields +40% citations (Princeton GEO paper).
    Pattern: H2/H3 as question -> direct answer in first 1-2 sentences.
    """
    sentences = nltk.sent_tokenize(following_text)
    if not sentences:
        return CriterionResult(
            criterion_id="CS2", criterion_name="Answer-first format",
            score=0, max_score=100, is_binary=False,
            human_summary="No content found under headings",
            technical_detail="Empty content blocks",
            evidence={}, checked=True,
        )

    # Check if heading is question-like
    is_question = heading_text.strip().endswith("?") or heading_text.lower().startswith(
        ("what", "how", "why", "when", "where", "which", "who", "can", "does", "is")
    )

    # Check if first sentence is a direct answer (short, declarative)
    first_sentence = sentences[0]
    word_count = len(first_sentence.split())
    is_direct_answer = 10 <= word_count <= 60  # 40-60 word ideal range

    # Score based on both signals
    score = 0
    if is_question:
        score += 40
    if is_direct_answer:
        score += 40
    if len(sentences) >= 2:
        score += 20  # Has supporting detail

    return CriterionResult(
        criterion_id="CS2", criterion_name="Answer-first format",
        score=min(100, score), max_score=100, is_binary=False,
        human_summary=f"{'Good' if score >= 60 else 'Needs improvement'}: "
                      f"{'Question-based headings' if is_question else 'Statement headings'}, "
                      f"{'direct answers' if is_direct_answer else 'no direct answer'} after headings",
        technical_detail=f"Question headings: {is_question}, "
                        f"First sentence words: {word_count}, "
                        f"Paragraphs after heading: {len(sentences)}",
        evidence={"is_question_heading": is_question, "first_sentence_words": word_count},
        checked=True,
    )
```

### Google PageSpeed Insights API Call
```python
# Source: Google PageSpeed Insights API v5 documentation
# https://developers.google.com/speed/docs/insights/v5/get-started
import httpx

async def check_core_web_vitals(self, url: str) -> CriterionResult:
    """Check Core Web Vitals via Google PageSpeed Insights API.

    Free tier: 25,000 requests/day, 240 requests/minute.
    No API key required for basic usage, but recommended.
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                "https://www.googleapis.com/pagespeedonline/v5/runPagespeed",
                params={
                    "url": url,
                    "category": "performance",
                    "strategy": "mobile",
                },
            )
            if resp.status_code != 200:
                return self._not_checked("S11", "Core Web Vitals (LCP)",
                    f"PageSpeed API returned {resp.status_code}")

            data = resp.json()
            # Extract LCP from Lighthouse audit
            lcp_ms = (data.get("lighthouseResult", {})
                      .get("audits", {})
                      .get("largest-contentful-paint", {})
                      .get("numericValue", None))

            if lcp_ms is None:
                return self._not_checked("S11", "Core Web Vitals (LCP)",
                    "LCP data not available")

            # Score: LCP < 2.5s = good, 2.5-4s = needs improvement, >4s = poor
            lcp_seconds = lcp_ms / 1000
            if lcp_seconds <= 2.5:
                score = 100
            elif lcp_seconds <= 4.0:
                score = int(100 - ((lcp_seconds - 2.5) / 1.5) * 50)
            else:
                score = max(0, int(50 - ((lcp_seconds - 4.0) / 4.0) * 50))

            return CriterionResult(
                criterion_id="S11", criterion_name="Core Web Vitals (LCP)",
                score=score, max_score=100, is_binary=False,
                human_summary=f"LCP: {lcp_seconds:.1f}s -- "
                    f"{'Good' if lcp_seconds <= 2.5 else 'Needs improvement' if lcp_seconds <= 4 else 'Poor'}",
                technical_detail=f"Largest Contentful Paint: {lcp_seconds:.2f}s "
                    f"(mobile). Good: <2.5s, Needs improvement: 2.5-4s, Poor: >4s",
                evidence={"lcp_ms": lcp_ms, "lcp_seconds": lcp_seconds},
                checked=True,
            )
    except Exception as e:
        return self._not_checked("S11", "Core Web Vitals (LCP)",
            f"PageSpeed API error: {str(e)[:200]}")
```

### Weakest-Link Score Aggregation
```python
def compute_optimization_score(
    self, page_category_scores: list[dict], visibility_score: int
) -> int:
    """Compute overall Optimization Score.

    1. Each page has 4 category scores.
    2. Weight categories: Crawlability 25%, Content 25%, Schema 20%, Authority 15%.
    3. AI Visibility 15% comes from the existing VisibilityScore.
    4. Aggregate across pages using weakest-link formula.

    Weakest-link formula: 0.6 * mean + 0.4 * min
    This ensures the worst page pulls the overall score down,
    encouraging fixing the worst pages first.
    """
    if not page_category_scores:
        return 0

    page_weighted_scores = []
    for page in page_category_scores:
        weighted = (
            page.get("crawlability", 0) * 0.25 +
            page.get("content_structure", 0) * 0.25 +
            page.get("structured_data", 0) * 0.20 +
            page.get("authority", 0) * 0.15
        )
        # Scale from 0-0.85 to 0-85 (authority weight covers 85%)
        page_weighted_scores.append(weighted)

    # Weakest-link aggregation across pages
    avg = sum(page_weighted_scores) / len(page_weighted_scores)
    minimum = min(page_weighted_scores)
    site_technical_score = 0.6 * avg + 0.4 * minimum

    # Add AI Visibility at 15%
    optimization_score = site_technical_score + (visibility_score * 0.15)

    return round(max(0, min(100, optimization_score)))
```

### Database Models
```python
# New models for Phase 6

class PageScore(Base):
    """Per-page scoring results for an audit."""
    __tablename__ = "page_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id = Column(UUID(as_uuid=True), ForeignKey("audits.id"), nullable=False, index=True)
    page_url = Column(String, nullable=False)
    page_title = Column(String, nullable=True)
    crawl_data = Column(JSONB, nullable=True)  # Per-page crawl result

    # Category scores (0-100)
    crawlability_score = Column(Integer, nullable=True)
    content_structure_score = Column(Integer, nullable=True)
    structured_data_score = Column(Integer, nullable=True)
    authority_score = Column(Integer, nullable=True)
    overall_page_score = Column(Integer, nullable=True)  # Weighted combination

    # Discovery metadata
    internal_link_count = Column(Integer, nullable=False, default=0)
    was_scored = Column(sa.Boolean, nullable=False, default=True)  # False = discovered but not scored

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    audit = relationship("Audit", backref="page_scores")
    criterion_results = relationship("CriterionResult", back_populates="page_score", cascade="all, delete-orphan")


class CriterionResult(Base):
    """Individual criterion score for a page."""
    __tablename__ = "criterion_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    page_score_id = Column(UUID(as_uuid=True), ForeignKey("page_scores.id"), nullable=False, index=True)
    criterion_id = Column(String, nullable=False)       # e.g., "C1", "CS3", "SD7"
    criterion_name = Column(String, nullable=False)      # e.g., "GPTBot access"
    category = Column(String, nullable=False)            # "crawlability", "content_structure", etc.
    score = Column(Integer, nullable=False)              # 0-100
    max_score = Column(Integer, nullable=False, default=100)
    is_binary = Column(sa.Boolean, nullable=False, default=False)
    human_summary = Column(Text, nullable=False)
    technical_detail = Column(Text, nullable=False)
    evidence = Column(JSONB, nullable=True)              # Machine-readable evidence
    checked = Column(sa.Boolean, nullable=False, default=True)  # False = could not check

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    page_score = relationship("PageScore", back_populates="criterion_results")
```

## Criteria Classification: Binary vs Gradient

Based on the nature of each criterion:

### Binary Criteria (0 or 100)
| ID | Criterion | Rationale |
|----|-----------|-----------|
| C1 | GPTBot access | Either allowed or blocked |
| C2 | ClaudeBot access | Either allowed or blocked |
| C3 | PerplexityBot access | Either allowed or blocked |
| C4 | OAI-SearchBot access | Either allowed or blocked |
| C5 | Claude-SearchBot access | Either allowed or blocked |
| C6 | Bingbot access | Either allowed or blocked |
| C7 | CCBot access | Either allowed or blocked |
| C8 | Google-Extended access | Either allowed or blocked |
| C11 | HTTP status code | Either 200 or not |
| S1 | SSL/HTTPS | Either present or not |
| S2 | Canonical tags | Either present or not |
| S5 | XML sitemap | Either exists or not |
| SD1 | Organization schema | Either present or not |
| SD12 | llms.txt presence | Either exists or not |
| SD13 | llms-full.txt presence | Either exists or not |

### Gradient Criteria (0-100 spectrum)
All remaining criteria: C9 (SSR), C10 (TTFB), C12 (Resource blockage), CS1-CS13 (all content), SD2-SD11 (schema quality), A1-A8 (authority), S3-S4 (meta quality), S6-S15 (SEO signals).

## Backlink Strategy: Proxy Signals

**Research finding:** No viable free backlink API exists. Common Crawl requires massive dataset downloads. OpenLinkProfiler's API is deprecated. Moz's free tier is extremely limited (10 requests/month).

**Recommendation:** Use proxy signals for S9 (Backlink profile) and S10 (Referring domains):

1. **Internal link quality (primary proxy):** Count and quality of internal links to/from each page. Pages with strong internal linking clusters have higher citation probability (2.7x, per research). This is available from the multi-page crawl data.

2. **sameAs links (secondary proxy):** Count of `sameAs` links in Organization schema pointing to authoritative platforms (LinkedIn, Wikipedia, G2, Trustpilot). More platforms = stronger entity signal.

3. **External link profile from page content:** Count outbound links to authoritative domains (`.edu`, `.gov`, Wikipedia, industry authorities) -- this is the "cites sources" signal from the Princeton GEO paper.

4. **Score S9/S10 as gradient (0-100):** Based on internal link count relative to site average, sameAs count, and outbound authority links. This gives a meaningful signal without paid API costs.

**Future upgrade path:** When revenue justifies it, integrate Moz API ($5/month starter) or DataForSEO (pay-per-query) for real DR/DA scores.

## External API Summary

| API | Free Tier | Rate Limit | Used For | Criteria |
|-----|-----------|------------|----------|----------|
| Google PageSpeed Insights v5 | Yes | 25K/day, 240/min | Core Web Vitals (LCP) | S11 |
| Google Knowledge Graph Search | Yes (limited) | Shared quota | Entity presence | A3 |
| Wikidata wbsearchentities | Yes (unlimited) | Reasonable use | QID lookup | A4 |
| Wikipedia API | Yes (unlimited) | Reasonable use | Wikipedia page check | A5 |
| No API needed | - | - | All other 49 criteria | All others |

**Important:** Only 4 of 53 criteria need external APIs. The remaining 49 criteria are computed from crawled HTML data using local analysis.

## Celery Pipeline Extension

The current pipeline has 5 stages. Phase 6 adds SCORING as stage 4.5 (after ANALYZING, before COMPLETED):

```
PENDING -> CRAWLING -> GENERATING_QUERIES -> DISPATCHING -> ANALYZING -> SCORING -> COMPLETED
```

**Key change:** The CRAWLING stage currently crawls one page. The multi-page crawl happens in the SCORING stage (or the CRAWLING stage is extended). The recommended approach is to keep the existing CRAWLING stage for the initial page (backward compatible) and add multi-page crawling within the SCORING stage, since the page scoring logic needs the crawled data anyway.

The SCORING stage:
1. Discover internal links from initial crawl_data
2. Select top pages by link count (up to CRAWL_CAP)
3. Crawl selected pages (new httpx + Playwright calls)
4. Score each page with all 4 scorers
5. Store PageScore and CriterionResult records
6. Compute and store OptimizationScore

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Keyword density scoring | Entity-based + structure-based scoring | 2024-2025 | Keyword stuffing is counterproductive for AI |
| Manual competitor research | NER extraction from AI responses | 2025 | Automated, data-driven competitor discovery |
| Generic SEO audits | AI-specific crawlability + extractability | 2025 (Otterly.ai) | SSR detection is the #1 technical factor |
| Single-score outputs | Multi-factor scores with evidence | 2025-2026 | Users need to know WHY, not just WHAT |
| Microdata/RDFa for structured data | JSON-LD exclusively | 2025 (Google rec) | JSON-LD is parseable without JS execution |

**Deprecated/outdated:**
- Legacy `geo_data_points/` system: 103/108 stubs, incompatible sync architecture, outdated criteria
- Keyword-based content scoring: AI engines are not keyword matchers
- Content volume as quality signal: Ahrefs study shows ~0.194 correlation (near zero)

## Open Questions

1. **Playwright in Docker**
   - What we know: Playwright requires system-level browser dependencies. The Dockerfile and docker-compose.yml need to install Chromium.
   - What's unclear: Whether the existing Docker setup already has Playwright browsers installed (playwright is in requirements.txt but may not have browser binaries).
   - Recommendation: Add `playwright install chromium --with-deps` to the backend Dockerfile. Use only Chromium (not Firefox/WebKit) to minimize image size.

2. **GOOGLE_PAGESPEED_API_KEY configuration**
   - What we know: PageSpeed API works without a key for basic usage but has lower rate limits.
   - What's unclear: Whether 25 calls per audit (one per page) will hit the unauthenticated rate limit.
   - Recommendation: Add `GOOGLE_API_KEY` to Settings as optional. Use it if present, fall back to unauthenticated if not. Document in `.env.example`.

3. **Multi-page crawl timing budget**
   - What we know: Current single-page audit takes ~4 minutes. Multi-page crawling + scoring could add significant time.
   - What's unclear: Exact timing for 25 pages with SSR detection + PageSpeed API calls.
   - Recommendation: Set a 10-minute timeout for the SCORING stage. Crawl pages concurrently (asyncio, max 5 concurrent). Run PageSpeed API calls sequentially (10-30s each, only for homepage to start). If scoring exceeds timeout, score what was crawled.

4. **Optimization Score storage**
   - What we know: Visibility Score has its own model/table. Optimization Score is a new parallel score.
   - What's unclear: Whether to add optimization_score to the existing VisibilityScore model or create a new model.
   - Recommendation: Create a new `OptimizationScore` model (parallel to `VisibilityScore`) with the overall score, per-category scores, and metadata. This keeps the two scoring systems independent and avoids modifying the existing working model.

## Sources

### Primary (HIGH confidence)
- Existing codebase: `backend/app/services/crawler_service.py` -- current crawl patterns and data extraction
- Existing codebase: `backend/app/tasks/audit_tasks.py` -- Celery pipeline stages
- Existing codebase: `backend/app/services/scoring_service.py` -- VisibilityScore computation pattern
- Existing codebase: `backend/app/schemas/crawl.py` -- CrawlResult schema with all extracted signals
- [Google PageSpeed Insights API v5](https://developers.google.com/speed/docs/insights/v5/get-started) -- Free API for Core Web Vitals
- [Google Knowledge Graph Search API](https://developers.google.com/knowledge-graph) -- Free entity lookup
- [Wikidata API: wbsearchentities](https://www.wikidata.org/wiki/Wikidata:Data_access) -- Free QID lookup
- [textstat PyPI](https://pypi.org/project/textstat/) -- Readability scoring

### Secondary (MEDIUM confidence)
- `.planning/research/ai-citation-factors.md` -- Research-backed impact data for scoring weights
- `.planning/research/ai-ready-standards.md` -- llms.txt spec, schema.org tiers, AI bot reference
- `.planning/research/geo-scoring-methods.md` -- Competitor scoring methodologies, Otterly/Evertune/HubSpot approaches
- [Playwright Python async API](https://playwright.dev/python/docs/api/class-browser) -- Headless browser for SSR detection
- [extruct documentation](https://github.com/scrapinghub/extruct) -- JSON-LD extraction
- [nltk.sent_tokenize](https://www.nltk.org/api/nltk.tokenize.html) -- Sentence tokenization

### Tertiary (LOW confidence)
- Common Crawl as backlink source -- not viable for real-time API use (massive dataset)
- OpenLinkProfiler -- API deprecated, web-only tool with limited data
- llms.txt impact on AI visibility -- specification exists but no AI provider confirms reading it

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all core libraries already in requirements.txt except nltk
- Architecture: HIGH -- follows existing service patterns (BaseScorer -> Celery pipeline -> DB models)
- Scoring criteria: HIGH -- all 53 criteria defined in roadmap with research backing
- External API integration: HIGH -- Google APIs are well-documented and free
- Backlink proxy strategy: MEDIUM -- proxy signals are reasonable but not as precise as real DR/DA
- Pitfalls: HIGH -- based on codebase analysis and known patterns from Phases 1-5

**Research date:** 2026-02-22
**Valid until:** 2026-03-22 (stable domain, criteria defined, APIs unlikely to change)
