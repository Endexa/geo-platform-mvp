"""CompetitorService -- orchestrates competitor URL resolution, crawling, and scoring.

Resolves brand names to URLs via a layered strategy (citation URL matching >
domain heuristic > Google Knowledge Graph), crawls competitor sites using
CrawlerService, scores them with the Phase 6 scoring pipeline, and stores
per-category averages on CompetitorAudit records.

Also handles cross-audit competitor persistence by linking DiscoveredCompetitor
records to Brand entities, enabling share-of-voice tracking over time and
side-by-side score comparison.
"""

import re
from urllib.parse import urlparse

import httpx
from loguru import logger
from rapidfuzz import fuzz
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.audit import Audit
from app.models.audit_query import AuditQuery
from app.models.brand import Brand
from app.models.competitor import CompetitorAudit, DiscoveredCompetitor
from app.models.engine_response import EngineResponse
from app.models.page_score import PageScore
from app.services.query_generator import QueryGeneratorService


# Corporate suffixes to strip from entity names for URL guessing
_CORPORATE_SUFFIXES = re.compile(
    r"\s*\b(Inc\.?|LLC\.?|Ltd\.?|Co\.?|Corp\.?|Corporation|Incorporated|Limited)\s*$",
    re.IGNORECASE,
)


def _clean_name(name: str) -> str:
    """Lowercase, strip spaces, commas, periods, corporate suffixes."""
    cleaned = _CORPORATE_SUFFIXES.sub("", name).strip()
    cleaned = cleaned.lower()
    cleaned = re.sub(r"[,.\s]+", "", cleaned)
    return cleaned


class CompetitorService:
    """Orchestrates competitor URL resolution, crawling, and scoring."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # URL Resolution (layered strategy from Research Pattern 4)
    # ------------------------------------------------------------------

    async def resolve_competitor_url(
        self, entity_name: str, citation_urls: list[str]
    ) -> str | None:
        """Resolve entity name to a website URL using layered strategy.

        Layers:
            1. Citation URL domain matching (rapidfuzz partial_ratio > 70)
            2. Domain heuristic: try https://www.{clean_name}.com
            3. Google Knowledge Graph API (if GOOGLE_API_KEY is set)
            4. Return None if all fail

        Args:
            entity_name: The brand/entity name to resolve.
            citation_urls: URLs extracted from AI response citations.

        Returns:
            Resolved URL string or None.
        """
        # Layer 1: Citation URL matching
        clean = _clean_name(entity_name)
        for url in citation_urls:
            try:
                from urllib.parse import urlparse

                domain = urlparse(url).netloc.lower()
                # Strip www. prefix for comparison
                domain_clean = domain.replace("www.", "")
                score = fuzz.partial_ratio(clean, domain_clean)
                if score > 70:
                    scheme = urlparse(url).scheme or "https"
                    resolved = f"{scheme}://{domain}"
                    logger.debug(
                        "Resolved '{}' via citation URL: {} (score={})",
                        entity_name,
                        resolved,
                        score,
                    )
                    return resolved
            except Exception:
                continue

        # Layer 2: Domain heuristic
        heuristic_url = f"https://www.{clean}.com"
        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=settings.COMPETITOR_URL_RESOLVE_TIMEOUT,
            ) as client:
                resp = await client.head(heuristic_url)
                if resp.status_code < 400:
                    logger.debug(
                        "Resolved '{}' via domain heuristic: {} (status={})",
                        entity_name,
                        heuristic_url,
                        resp.status_code,
                    )
                    return heuristic_url
        except Exception:
            pass

        # Layer 3: Google Knowledge Graph API
        if settings.GOOGLE_API_KEY:
            try:
                kg_url = (
                    "https://kgsearch.googleapis.com/v1/entities:search"
                    f"?query={entity_name}&key={settings.GOOGLE_API_KEY}"
                    "&limit=1&types=Organization"
                )
                async with httpx.AsyncClient(
                    timeout=settings.COMPETITOR_URL_RESOLVE_TIMEOUT
                ) as client:
                    resp = await client.get(kg_url)
                    if resp.status_code == 200:
                        data = resp.json()
                        elements = data.get("itemListElement", [])
                        if elements:
                            result = elements[0].get("result", {})
                            # Try detailedDescription.url first, then result.url
                            detail = result.get("detailedDescription", {})
                            resolved = detail.get("url") or result.get("url")
                            if resolved:
                                logger.debug(
                                    "Resolved '{}' via Knowledge Graph: {}",
                                    entity_name,
                                    resolved,
                                )
                                return resolved
            except Exception as e:
                logger.debug(
                    "Knowledge Graph lookup failed for '{}': {}",
                    entity_name,
                    str(e),
                )

        logger.debug("Could not resolve URL for entity '{}'", entity_name)
        return None

    # ------------------------------------------------------------------
    # Competitor Crawl + Score
    # ------------------------------------------------------------------

    async def crawl_and_score_competitor(
        self, parent_audit_id: str, competitor: DiscoveredCompetitor
    ) -> CompetitorAudit | None:
        """Crawl and score a single competitor site.

        1. Resolve URL if not already resolved
        2. Create CompetitorAudit record
        3. Crawl competitor pages (up to COMPETITOR_CRAWL_CAP)
        4. Run all 4 category scorers on each page
        5. Compute per-category averages and store on CompetitorAudit
        6. Return CompetitorAudit record

        Args:
            parent_audit_id: The parent audit UUID.
            competitor: The DiscoveredCompetitor ORM record.

        Returns:
            CompetitorAudit record or None if URL cannot be resolved.
        """
        # Ensure URL is resolved
        if not competitor.resolved_url:
            # Gather citation URLs for this audit
            citation_urls = self._gather_citation_urls(parent_audit_id)
            url = await self.resolve_competitor_url(
                competitor.entity_name, citation_urls
            )
            if url:
                competitor.resolved_url = url
            else:
                logger.info(
                    "Competitor '{}': could not resolve URL, skipping",
                    competitor.entity_name,
                )
                return None

        # Create CompetitorAudit record
        comp_audit = CompetitorAudit(
            parent_audit_id=parent_audit_id,
            competitor_name=competitor.entity_name,
            competitor_url=competitor.resolved_url,
            status="crawling",
        )
        self.db.add(comp_audit)
        self.db.flush()

        # Link competitor to audit
        competitor.competitor_audit_id = comp_audit.id
        competitor.is_crawled = True

        try:
            # Crawl competitor pages
            from app.services.crawler_service import CrawlerService

            crawler = CrawlerService()
            homepage_result = await crawler.crawl(competitor.resolved_url)
            homepage_data = homepage_result.model_dump()

            crawled_pages = [homepage_data]

            # Crawl additional pages if available (up to COMPETITOR_CRAWL_CAP - 1)
            cap = settings.COMPETITOR_CRAWL_CAP
            if cap > 1:
                # Discover internal links from homepage
                from app.services.scoring.scoring_orchestrator import (
                    ScoringOrchestrator,
                )

                temp_orch = ScoringOrchestrator(self.db)
                discovered_links = temp_orch._discover_internal_links(
                    html=homepage_data.get("main_content", ""),
                    base_url=homepage_data.get("url", ""),
                    domain=homepage_data.get("domain", ""),
                )
                # Pick top pages by link count, excluding homepage
                homepage_norm = temp_orch._normalize_url(
                    homepage_data.get("url", "")
                )
                other_pages = [
                    (url, count)
                    for url, count in discovered_links
                    if temp_orch._normalize_url(url) != homepage_norm
                ]
                urls_to_crawl = [url for url, _ in other_pages[: cap - 1]]

                if urls_to_crawl:
                    additional = await crawler.crawl_multiple(
                        start_url=competitor.resolved_url,
                        urls=urls_to_crawl,
                        max_concurrent=3,
                    )
                    for result in additional:
                        crawled_pages.append(result.model_dump())

            # Store crawl data on CompetitorAudit
            comp_audit.crawl_data = {
                "pages": len(crawled_pages),
                "homepage_url": competitor.resolved_url,
            }
            comp_audit.status = "scoring"
            self.db.flush()

            # Score each page using all 4 category scorers
            scorers = self._build_scorers()

            # Collect per-page per-category scores
            all_category_scores: dict[str, list[float]] = {
                "crawlability": [],
                "content_structure": [],
                "structured_data": [],
                "authority": [],
            }

            for page_data in crawled_pages:
                for category, scorer in scorers.items():
                    try:
                        criterion_results = await scorer.score_page(page_data)
                        category_score = scorer.compute_category_score(
                            criterion_results
                        )
                        all_category_scores[category].append(category_score)
                    except Exception as e:
                        logger.warning(
                            "Competitor '{}': scorer {} failed on page {}: {}",
                            competitor.entity_name,
                            category,
                            page_data.get("url", "unknown"),
                            str(e),
                        )

            # Compute per-category averages
            def _avg(scores: list[float]) -> int | None:
                if not scores:
                    return None
                return round(sum(scores) / len(scores))

            comp_audit.crawlability_avg = _avg(
                all_category_scores["crawlability"]
            )
            comp_audit.content_structure_avg = _avg(
                all_category_scores["content_structure"]
            )
            comp_audit.structured_data_avg = _avg(
                all_category_scores["structured_data"]
            )
            comp_audit.authority_avg = _avg(all_category_scores["authority"])
            comp_audit.pages_scored = len(crawled_pages)

            # Compute optimization score (weighted average of category averages)
            weights = {
                "crawlability": 0.25,
                "content_structure": 0.25,
                "structured_data": 0.20,
                "authority": 0.15,
            }
            weighted_sum = 0.0
            active_weight = 0.0
            for cat, weight in weights.items():
                avg = _avg(all_category_scores[cat])
                if avg is not None:
                    weighted_sum += avg * weight
                    active_weight += weight
            if active_weight > 0:
                comp_audit.optimization_score = round(
                    weighted_sum / active_weight
                )
            else:
                comp_audit.optimization_score = None

            comp_audit.status = "completed"
            self.db.flush()

            logger.info(
                "Competitor '{}': scored {} pages, optimization={}",
                competitor.entity_name,
                comp_audit.pages_scored,
                comp_audit.optimization_score,
            )
            return comp_audit

        except Exception as e:
            logger.error(
                "Competitor '{}': crawl/score failed: {}",
                competitor.entity_name,
                str(e),
            )
            comp_audit.status = "failed"
            self.db.flush()
            return None

    # ------------------------------------------------------------------
    # Crawl Top Competitors
    # ------------------------------------------------------------------

    async def crawl_top_competitors(
        self, audit_id: str, max_competitors: int | None = None
    ) -> list[CompetitorAudit]:
        """Resolve URLs and crawl+score top competitors for an audit.

        1. Query DiscoveredCompetitor records (non-user-brand, not yet crawled)
        2. Resolve URLs for each
        3. Crawl and score each competitor sequentially
        4. Commit results

        Args:
            audit_id: The audit UUID.
            max_competitors: Override for COMPETITOR_MAX_COUNT setting.

        Returns:
            List of CompetitorAudit records for successfully crawled competitors.
        """
        limit = max_competitors or settings.COMPETITOR_MAX_COUNT

        # Query top competitors by mention_count
        competitors = (
            self.db.query(DiscoveredCompetitor)
            .filter(DiscoveredCompetitor.audit_id == audit_id)
            .filter(DiscoveredCompetitor.is_user_brand.is_(False))
            .filter(DiscoveredCompetitor.is_crawled.is_(False))
            .order_by(DiscoveredCompetitor.mention_count.desc())
            .limit(limit)
            .all()
        )

        if not competitors:
            logger.info("Audit {}: no competitors to crawl", audit_id)
            return []

        # Gather citation URLs once for URL resolution
        citation_urls = self._gather_citation_urls(audit_id)

        # Resolve URLs for all competitors first
        for competitor in competitors:
            if not competitor.resolved_url:
                url = await self.resolve_competitor_url(
                    competitor.entity_name, citation_urls
                )
                if url:
                    competitor.resolved_url = url

        self.db.flush()

        # Crawl and score each competitor sequentially (avoid rate limiting)
        results: list[CompetitorAudit] = []
        for competitor in competitors:
            comp_audit = await self.crawl_and_score_competitor(
                audit_id, competitor
            )
            if comp_audit:
                results.append(comp_audit)

        self.db.commit()

        logger.info(
            "Audit {}: crawled {} of {} competitors",
            audit_id,
            len(results),
            len(competitors),
        )
        return results

    # ------------------------------------------------------------------
    # Leaderboard Query
    # ------------------------------------------------------------------

    def get_leaderboard(self, audit_id: str) -> dict:
        """Build competitor leaderboard data for an audit.

        Args:
            audit_id: The audit UUID.

        Returns:
            Dict with audit_id, user_brand_name, total_entities,
            competitors list, and competitor_audits list.
        """
        # Query all discovered competitors
        competitors = (
            self.db.query(DiscoveredCompetitor)
            .filter(DiscoveredCompetitor.audit_id == audit_id)
            .order_by(DiscoveredCompetitor.mention_count.desc())
            .all()
        )

        # Query competitor audits
        comp_audits = (
            self.db.query(CompetitorAudit)
            .filter(CompetitorAudit.parent_audit_id == audit_id)
            .all()
        )

        # Extract user brand name from audit crawl_data
        audit = self.db.query(Audit).filter(Audit.id == audit_id).first()
        user_brand_name = ""
        if audit and audit.crawl_data:
            query_gen = QueryGeneratorService()
            user_brand_name = query_gen.extract_brand_name(audit.crawl_data)

        # Build competitors list
        competitor_entries = []
        for c in competitors:
            competitor_entries.append({
                "entity_name": c.entity_name,
                "entity_type": c.entity_type,
                "mention_count": c.mention_count,
                "share_of_voice": float(c.share_of_voice),
                "engines_mentioned_in": c.engines_mentioned_in or {},
                "queries_mentioned_in": c.queries_mentioned_in or [],
                "resolved_url": c.resolved_url,
                "is_crawled": c.is_crawled,
                "is_user_brand": c.is_user_brand,
                "competitor_audit_id": (
                    str(c.competitor_audit_id) if c.competitor_audit_id else None
                ),
            })

        # Build competitor audit summaries
        audit_summaries = []
        for ca in comp_audits:
            audit_summaries.append({
                "id": str(ca.id),
                "competitor_name": ca.competitor_name,
                "competitor_url": ca.competitor_url,
                "optimization_score": ca.optimization_score,
                "crawlability_avg": ca.crawlability_avg,
                "content_structure_avg": ca.content_structure_avg,
                "structured_data_avg": ca.structured_data_avg,
                "authority_avg": ca.authority_avg,
                "pages_scored": ca.pages_scored,
                "status": ca.status,
                "created_at": (
                    ca.created_at.isoformat() if ca.created_at else ""
                ),
            })

        return {
            "audit_id": str(audit_id),
            "user_brand_name": user_brand_name,
            "total_entities": len(competitors),
            "competitors": competitor_entries,
            "competitor_audits": audit_summaries,
        }

    # ------------------------------------------------------------------
    # Brand Linking (cross-audit competitor persistence)
    # ------------------------------------------------------------------

    def link_competitor_to_brand(
        self, db: Session, competitor: DiscoveredCompetitor, user_id: str
    ) -> None:
        """Link a DiscoveredCompetitor to a Brand record.

        Matching strategy (in priority order):
            1. Domain match (strongest signal): extract domain from resolved_url,
               find Brand with matching domain for this user.
            2. Exact name match (case-insensitive): find Brand where lower(name)
               matches lower(entity_name).
            3. Fuzzy name match: rapidfuzz token_set_ratio > 90 against all
               user's Brands.
            4. Create new Brand: if no match found.

        Args:
            db: SQLAlchemy session.
            competitor: The DiscoveredCompetitor ORM record.
            user_id: The owner user UUID string.
        """
        extracted_domain = None
        if competitor.resolved_url:
            parsed = urlparse(competitor.resolved_url)
            extracted_domain = parsed.netloc.lower().replace("www.", "")

        # Strategy 1: Domain match
        if extracted_domain:
            brand = (
                db.query(Brand)
                .filter(Brand.user_id == user_id)
                .filter(func.lower(Brand.domain) == extracted_domain)
                .first()
            )
            if brand:
                competitor.competitor_brand_id = brand.id
                logger.debug(
                    "Linked '{}' to brand '{}' via domain match",
                    competitor.entity_name,
                    brand.name,
                )
                return

        # Strategy 2: Exact name match (case-insensitive)
        entity_lower = competitor.entity_name.lower()
        brand = (
            db.query(Brand)
            .filter(Brand.user_id == user_id)
            .filter(func.lower(Brand.name) == entity_lower)
            .first()
        )
        if brand:
            competitor.competitor_brand_id = brand.id
            logger.debug(
                "Linked '{}' to brand '{}' via exact name match",
                competitor.entity_name,
                brand.name,
            )
            return

        # Strategy 3: Fuzzy name match (token_set_ratio > 90)
        all_brands = db.query(Brand).filter(Brand.user_id == user_id).all()
        best_score = 0
        best_brand = None
        for b in all_brands:
            score = fuzz.token_set_ratio(b.name, competitor.entity_name)
            if score > best_score:
                best_score = score
                best_brand = b
        if best_score > 90 and best_brand is not None:
            competitor.competitor_brand_id = best_brand.id
            logger.debug(
                "Linked '{}' to brand '{}' via fuzzy match (score={})",
                competitor.entity_name,
                best_brand.name,
                best_score,
            )
            return

        # Strategy 4: Create new Brand
        new_brand = Brand(
            user_id=user_id,
            name=competitor.entity_name,
            domain=extracted_domain or "",
            url=competitor.resolved_url or "",
            is_competitor=True,
        )
        db.add(new_brand)
        db.flush()
        competitor.competitor_brand_id = new_brand.id
        logger.debug(
            "Created new competitor brand '{}' for user {}",
            competitor.entity_name,
            user_id,
        )

    def link_audit_competitors_to_brands(
        self, db: Session, audit_id: str, user_id: str
    ) -> int:
        """Link all unlinked DiscoveredCompetitor records for an audit to Brands.

        Args:
            db: SQLAlchemy session.
            audit_id: The audit UUID string.
            user_id: The owner user UUID string.

        Returns:
            Count of newly linked competitors.
        """
        unlinked = (
            db.query(DiscoveredCompetitor)
            .filter(DiscoveredCompetitor.audit_id == audit_id)
            .filter(DiscoveredCompetitor.competitor_brand_id.is_(None))
            .all()
        )

        count = 0
        for comp in unlinked:
            self.link_competitor_to_brand(db, comp, user_id)
            count += 1

        logger.info(
            "Audit {}: linked {} competitors to brands", audit_id, count
        )
        return count

    # ------------------------------------------------------------------
    # SOV Trend Query (cross-audit time series)
    # ------------------------------------------------------------------

    @staticmethod
    def get_competitor_sov_trend(
        db: Session, brand_id: str, user_id: str
    ) -> list[dict]:
        """Query share-of-voice trend for a competitor brand across audits.

        Joins DiscoveredCompetitor with Audit to get the audit date,
        filtered by user_id and competitor_brand_id.

        Args:
            db: SQLAlchemy session.
            brand_id: The Brand UUID string.
            user_id: The owner user UUID string.

        Returns:
            List of dicts with date, share_of_voice, mention_count, audit_id,
            ordered by audit date ascending.
        """
        results = (
            db.query(DiscoveredCompetitor, Audit.created_at, Audit.id)
            .join(Audit, DiscoveredCompetitor.audit_id == Audit.id)
            .filter(Audit.user_id == user_id)
            .filter(DiscoveredCompetitor.competitor_brand_id == brand_id)
            .order_by(Audit.created_at.asc())
            .all()
        )

        trend = []
        for comp, audit_date, audit_id in results:
            trend.append({
                "date": audit_date.isoformat() if audit_date else "",
                "share_of_voice": float(comp.share_of_voice),
                "mention_count": comp.mention_count,
                "audit_id": str(audit_id),
            })

        return trend

    # ------------------------------------------------------------------
    # Score Comparison (site vs competitors side-by-side)
    # ------------------------------------------------------------------

    def get_score_comparison(
        self, db: Session, audit_id: str, user_id: str
    ) -> dict:
        """Build side-by-side score comparison between user's site and competitors.

        Loads the Audit record for the user's site scores and all completed
        CompetitorAudit records for competitor scores.

        Site category scores are computed by averaging PageScore records for
        the audit (same aggregation used by the scoring pipeline).

        Args:
            db: SQLAlchemy session.
            audit_id: The audit UUID string.
            user_id: The owner user UUID string.

        Returns:
            Dict with 'site' (name, url, optimization_score, category scores)
            and 'competitors' list (same fields per completed competitor).
        """
        audit = db.query(Audit).filter(Audit.id == audit_id).first()
        if not audit:
            return {"site": {}, "competitors": []}

        # Compute site category averages from PageScore records
        page_scores = (
            db.query(PageScore)
            .filter(PageScore.audit_id == audit_id)
            .filter(PageScore.was_scored.is_(True))
            .all()
        )

        def _avg_field(records, field_name):
            values = [
                getattr(r, field_name)
                for r in records
                if getattr(r, field_name) is not None
            ]
            if not values:
                return None
            return round(sum(values) / len(values))

        site_name = audit.url
        if audit.brand:
            site_name = audit.brand.name

        site_data = {
            "name": site_name,
            "url": audit.url,
            "optimization_score": audit.optimization_score,
            "crawlability": _avg_field(page_scores, "crawlability_score"),
            "content_structure": _avg_field(page_scores, "content_structure_score"),
            "structured_data": _avg_field(page_scores, "structured_data_score"),
            "authority": _avg_field(page_scores, "authority_score"),
        }

        # Load completed competitor audits
        comp_audits = (
            db.query(CompetitorAudit)
            .filter(CompetitorAudit.parent_audit_id == audit_id)
            .filter(CompetitorAudit.status == "completed")
            .all()
        )

        competitors_data = []
        for ca in comp_audits:
            competitors_data.append({
                "name": ca.competitor_name,
                "url": ca.competitor_url,
                "optimization_score": ca.optimization_score,
                "crawlability": ca.crawlability_avg,
                "content_structure": ca.content_structure_avg,
                "structured_data": ca.structured_data_avg,
                "authority": ca.authority_avg,
            })

        return {
            "site": site_data,
            "competitors": competitors_data,
        }

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _gather_citation_urls(self, audit_id: str) -> list[str]:
        """Gather all citation URLs from EngineResponse records for an audit.

        Args:
            audit_id: The audit UUID.

        Returns:
            Flat list of all citation URLs.
        """
        responses = (
            self.db.query(EngineResponse)
            .join(AuditQuery, EngineResponse.audit_query_id == AuditQuery.id)
            .filter(AuditQuery.audit_id == audit_id)
            .filter(EngineResponse.citations.isnot(None))
            .all()
        )

        urls: list[str] = []
        for resp in responses:
            if isinstance(resp.citations, list):
                urls.extend(resp.citations)

        return urls

    def _build_scorers(self) -> dict:
        """Build scorer instances for all 4 categories.

        Uses the same conditional import pattern as audit_tasks.py
        so that missing scorers are gracefully skipped.

        Returns:
            Dict of category -> BaseScorer instance.
        """
        scorers = {}

        try:
            from app.services.scoring.crawlability_scorer import (
                CrawlabilityScorer,
            )

            scorers["crawlability"] = CrawlabilityScorer()
        except ImportError:
            logger.warning("CrawlabilityScorer not available for competitor scoring")

        try:
            from app.services.scoring.content_structure_scorer import (
                ContentStructureScorer,
            )

            scorers["content_structure"] = ContentStructureScorer()
        except ImportError:
            logger.warning(
                "ContentStructureScorer not available for competitor scoring"
            )

        try:
            from app.services.scoring.structured_data_scorer import (
                StructuredDataScorer,
            )

            scorers["structured_data"] = StructuredDataScorer()
        except ImportError:
            logger.warning(
                "StructuredDataScorer not available for competitor scoring"
            )

        try:
            from app.services.scoring.authority_scorer import AuthorityScorer

            scorers["authority"] = AuthorityScorer()
        except ImportError:
            logger.warning("AuthorityScorer not available for competitor scoring")

        return scorers
