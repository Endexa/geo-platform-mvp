"""ScoringOrchestrator -- coordinates multi-page crawl, scoring, and aggregation.

Discovers internal links from the initial crawl, selects top pages by link
count (up to configurable cap), crawls them, runs all registered scorers on
each page, stores results in the DB, and computes the final optimization score
using weakest-link aggregation.
"""

import asyncio
import re
from urllib.parse import urljoin, urlparse, urlunparse

from loguru import logger

from app.core.config import settings
from app.models.criterion_result import CriterionResult as CriterionResultModel
from app.models.page_score import PageScore
from app.services.scoring.base_scorer import BaseScorer, ScoringCriterionResult


# URL patterns to skip when discovering internal links
SKIP_URL_PATTERNS = re.compile(
    r"(/login|/signup|/register|/admin|/api/|/assets/|/static/|"
    r"/cart|/checkout|/account|/wp-admin|/wp-json)"
    r"|\.(?:pdf|jpg|jpeg|png|gif|svg|css|js|ico|woff2?|ttf|eot|mp[34]|zip|gz)$",
    re.IGNORECASE,
)


class ScoringOrchestrator:
    """Orchestrates multi-page crawling, per-page scoring, and aggregation.

    Category scorers are registered by Plans 02-05. The orchestrator runs
    all available scorers on each crawled page and persists results.

    Attributes:
        CATEGORY_WEIGHTS: Weight of each scoring category in the final score.
    """

    CATEGORY_WEIGHTS: dict[str, float] = {
        "crawlability": 0.25,
        "content_structure": 0.25,
        "structured_data": 0.20,
        "authority": 0.15,
        "ai_visibility": 0.15,
    }

    def __init__(self, db):
        """Initialize the orchestrator.

        Args:
            db: SQLAlchemy session for persisting score results.
        """
        self.db = db
        self.scorers: dict[str, BaseScorer] = {}

    def register_scorer(self, category: str, scorer: BaseScorer) -> None:
        """Register a category scorer.

        Args:
            category: Category key (e.g., "crawlability", "content_structure").
            scorer: BaseScorer instance for the category.
        """
        self.scorers[category] = scorer
        logger.info("Registered scorer for category: {}", category)

    async def score_audit(
        self, audit_id: str, crawl_data: dict, visibility_score: int
    ) -> dict:
        """Main entry point: discover pages, crawl, score, persist, aggregate.

        Args:
            audit_id: UUID of the audit being scored.
            crawl_data: Initial crawl result dict (from CrawlerService.crawl()).
            visibility_score: Overall visibility score (0-100) from mention analysis.

        Returns:
            Dict with optimization_score, page_count, pages_scored, pages_discovered.
        """
        from app.services.crawler_service import CrawlerService

        homepage_url = crawl_data.get("url", "")
        domain = crawl_data.get("domain", "")
        html = crawl_data.get("main_content", "")

        # Step 1: Discover internal links from initial crawl data
        # We use the main_content as a fallback -- ideally we'd have the full HTML
        # but we work with what the crawl_data provides
        discovered_links = self._discover_internal_links(
            html=html, base_url=homepage_url, domain=domain
        )
        logger.info(
            "Audit {}: discovered {} internal links", audit_id, len(discovered_links)
        )

        # Step 2: Select top pages by link count (homepage always included)
        cap = settings.SCORING_CRAWL_CAP
        # Filter out the homepage itself from discovered links
        other_pages = [
            (url, count)
            for url, count in discovered_links
            if self._normalize_url(url) != self._normalize_url(homepage_url)
        ]
        pages_to_score = other_pages[: cap - 1]  # Reserve one slot for homepage
        all_discovered_urls = [url for url, _ in other_pages]

        # Step 3: Crawl selected pages
        crawled_pages: list[dict] = [crawl_data]  # Homepage already crawled
        if pages_to_score:
            crawler = CrawlerService()
            urls_to_crawl = [url for url, _ in pages_to_score]
            crawl_results = await crawler.crawl_multiple(
                start_url=homepage_url,
                urls=urls_to_crawl,
                max_concurrent=5,
            )
            for result in crawl_results:
                crawled_pages.append(result.model_dump())

        logger.info(
            "Audit {}: crawled {} pages (cap={})",
            audit_id,
            len(crawled_pages),
            cap,
        )

        # Step 4: Score each crawled page
        page_category_scores: list[dict] = []
        for page_data in crawled_pages:
            page_url = page_data.get("url", "")
            page_title = page_data.get("title", "")

            # Run all registered scorers
            category_results = await self._score_page(page_data)

            # Store PageScore record
            page_score = PageScore(
                audit_id=audit_id,
                page_url=page_url,
                page_title=page_title,
                crawl_data=page_data,
                was_scored=True,
                internal_link_count=0,
            )

            # Populate per-category scores
            category_scores_dict: dict[str, float] = {}
            for category, (score, results) in category_results.items():
                category_scores_dict[category] = score
                # Set category score on PageScore
                score_col = f"{category}_score"
                if hasattr(page_score, score_col):
                    setattr(page_score, score_col, round(score))

                # Store CriterionResult records
                for r in results:
                    criterion = CriterionResultModel(
                        page_score_id=page_score.id,
                        criterion_id=r.criterion_id,
                        criterion_name=r.criterion_name,
                        category=category,
                        score=r.score,
                        max_score=r.max_score,
                        is_binary=r.is_binary,
                        human_summary=r.human_summary,
                        technical_detail=r.technical_detail,
                        evidence=r.evidence,
                        checked=r.checked,
                    )
                    page_score.criterion_results.append(criterion)

            # Compute overall page score (from scored categories only)
            if category_scores_dict:
                weighted = sum(
                    category_scores_dict.get(cat, 0) * w
                    for cat, w in self.CATEGORY_WEIGHTS.items()
                    if cat in category_scores_dict
                )
                total_weight = sum(
                    w
                    for cat, w in self.CATEGORY_WEIGHTS.items()
                    if cat in category_scores_dict
                )
                page_score.overall_page_score = (
                    round(weighted / total_weight) if total_weight > 0 else 0
                )

            self.db.add(page_score)
            page_category_scores.append(category_scores_dict)

            logger.debug(
                "Audit {}: scored page {} -> {}",
                audit_id,
                page_url,
                category_scores_dict,
            )

        # Step 5: Store discovered-but-not-scored pages
        scored_urls = {self._normalize_url(p.get("url", "")) for p in crawled_pages}
        for url in all_discovered_urls:
            if self._normalize_url(url) not in scored_urls:
                unsored_page = PageScore(
                    audit_id=audit_id,
                    page_url=url,
                    was_scored=False,
                    internal_link_count=0,
                )
                self.db.add(unsored_page)

        self.db.flush()

        # Step 6: Compute final optimization score
        optimization_score = self.compute_optimization_score(
            page_category_scores, visibility_score
        )

        logger.info(
            "Audit {}: optimization_score={}, pages_scored={}, pages_discovered={}",
            audit_id,
            optimization_score,
            len(crawled_pages),
            len(all_discovered_urls) + 1,  # +1 for homepage
        )

        return {
            "optimization_score": optimization_score,
            "page_count": len(crawled_pages),
            "pages_scored": len(crawled_pages),
            "pages_discovered": len(all_discovered_urls) + 1,
        }

    async def _score_page(
        self, page_data: dict
    ) -> dict[str, tuple[float, list[ScoringCriterionResult]]]:
        """Run all registered scorers on a single page.

        Args:
            page_data: Crawl result dict for the page.

        Returns:
            Dict of category -> (category_score, list[ScoringCriterionResult]).
        """
        results: dict[str, tuple[float, list[ScoringCriterionResult]]] = {}
        for category, scorer in self.scorers.items():
            try:
                criterion_results = await scorer.score_page(page_data)
                category_score = scorer.compute_category_score(criterion_results)
                results[category] = (category_score, criterion_results)
            except Exception as e:
                logger.error(
                    "Scorer {} failed on page {}: {}",
                    category,
                    page_data.get("url", "unknown"),
                    str(e),
                )
                results[category] = (0.0, [])
        return results

    def _discover_internal_links(
        self, html: str, base_url: str, domain: str
    ) -> list[tuple[str, int]]:
        """Extract internal links with count, sorted descending by count.

        Normalizes URLs (strips fragments, trailing slashes). Skips
        non-content URLs (login, admin, assets, etc.) and non-same-domain.

        Args:
            html: HTML content (or text content) of the page.
            base_url: Base URL for resolving relative links.
            domain: Domain to filter same-domain links.

        Returns:
            List of (url, count) tuples, sorted by count descending.
        """
        from collections import Counter

        from bs4 import BeautifulSoup

        # Parse HTML to extract links
        soup = BeautifulSoup(html, "lxml")
        link_counter: Counter[str] = Counter()

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]

            # Resolve relative URLs
            try:
                full_url = urljoin(base_url, href)
            except Exception:
                continue

            parsed = urlparse(full_url)

            # Same domain only
            if parsed.netloc and parsed.netloc != domain:
                continue

            # Skip non-content URLs
            if SKIP_URL_PATTERNS.search(full_url):
                continue

            # Skip non-http schemes
            if parsed.scheme not in ("http", "https", ""):
                continue

            # Normalize: strip fragment, trailing slash
            normalized = self._normalize_url(full_url)
            if normalized:
                link_counter[normalized] += 1

        # Sort by count descending
        return sorted(link_counter.items(), key=lambda x: x[1], reverse=True)

    def _normalize_url(self, url: str) -> str:
        """Normalize a URL by stripping fragment and trailing slash.

        Args:
            url: URL to normalize.

        Returns:
            Normalized URL string.
        """
        parsed = urlparse(url)
        # Strip fragment, normalize path
        path = parsed.path.rstrip("/") or "/"
        normalized = urlunparse(
            (parsed.scheme, parsed.netloc, path, parsed.params, parsed.query, "")
        )
        return normalized

    def compute_optimization_score(
        self, page_category_scores: list[dict], visibility_score: int
    ) -> int:
        """Compute weighted optimization score with weakest-link aggregation.

        Formula:
        1. For each page, compute weighted category score
           (crawlability*0.25 + content_structure*0.25 + structured_data*0.20 + authority*0.15)
        2. Aggregate across pages: weakest_link = 0.6 * mean + 0.4 * min
        3. Add AI visibility: site_technical_score + visibility_score * 0.15
        4. Clamp to 0-100, return rounded int

        Args:
            page_category_scores: List of dicts, each mapping category -> score (0-100).
            visibility_score: Overall visibility score (0-100).

        Returns:
            Final optimization score as int (0-100).
        """
        if not page_category_scores:
            # No pages scored -- return visibility contribution only
            return max(0, min(100, round(visibility_score * 0.15)))

        # Technical category weights (excluding ai_visibility which uses visibility_score)
        technical_weights = {
            "crawlability": 0.25,
            "content_structure": 0.25,
            "structured_data": 0.20,
            "authority": 0.15,
        }
        total_technical_weight = sum(technical_weights.values())  # 0.85

        page_scores: list[float] = []
        for page_cats in page_category_scores:
            weighted_sum = 0.0
            active_weight = 0.0
            for cat, weight in technical_weights.items():
                if cat in page_cats:
                    weighted_sum += page_cats[cat] * weight
                    active_weight += weight
            if active_weight > 0:
                # Normalize by active weight so missing categories don't penalize
                page_scores.append(weighted_sum / active_weight * total_technical_weight)
            else:
                page_scores.append(0.0)

        # Weakest-link aggregation across pages
        if page_scores:
            mean_score = sum(page_scores) / len(page_scores)
            min_score = min(page_scores)
            site_technical_score = 0.6 * mean_score + 0.4 * min_score
        else:
            site_technical_score = 0.0

        # Add AI visibility contribution
        final_score = site_technical_score + visibility_score * 0.15

        return max(0, min(100, round(final_score)))
