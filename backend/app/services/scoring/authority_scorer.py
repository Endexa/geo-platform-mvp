"""AuthorityScorer -- evaluates E-E-A-T markers and SEO fundamentals.

Implements 23 criteria:
- A1-A8: E-E-A-T / Entity signals (author bios, dates, Knowledge Graph,
  Wikidata, Wikipedia, review profiles, brand signal, composite)
- S1-S15: SEO fundamentals (SSL, canonical, meta, sitemap, OG tags, mobile,
  internal links, backlink proxies, CWV, URL structure, alt text, broken links,
  orphan pages)

Authority is 15% of the Optimization Score. These signals directly impact
whether AI engines trust and cite a source (Princeton GEO research: citations
correlate with perceived authority and structured identity signals).

External APIs (Google Knowledge Graph, Wikidata, Wikipedia, PageSpeed Insights)
are called with graceful degradation -- failures return _not_checked, not score=0.
Backlink criteria (S9, S10) use proxy signals instead of paid APIs.
"""

import asyncio
import json
import re
from urllib.parse import quote, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from loguru import logger

from app.core.config import settings
from app.services.scoring.base_scorer import BaseScorer, ScoringCriterionResult

# Review platforms to check for entity presence
REVIEW_PLATFORMS = [
    "g2.com",
    "trustpilot.com",
    "capterra.com",
    "glassdoor.com",
    "yelp.com",
    "producthunt.com",
    "sourceforge.net",
    "tripadvisor.com",
]

# Authoritative domains for outbound link scoring
AUTHORITATIVE_DOMAINS = {
    ".edu",
    ".gov",
    "wikipedia.org",
    "who.int",
    "nih.gov",
    "cdc.gov",
    "nature.com",
    "sciencedirect.com",
    "pubmed.ncbi.nlm.nih.gov",
}


class AuthorityScorer(BaseScorer):
    """Scores pages on 23 authority criteria (8 E-E-A-T + 15 SEO fundamentals).

    External API calls use an asyncio semaphore (max 3 concurrent) to avoid
    rate limiting. All API failures degrade gracefully to _not_checked.

    Attributes:
        _api_semaphore: Limits concurrent external API calls.
        _cwv_cache: Caches PageSpeed result per domain (only call once).
        _sitemap_cache: Caches sitemap check result per domain.
    """

    def __init__(self):
        self._api_semaphore = asyncio.Semaphore(3)
        self._cwv_cache: dict[str, ScoringCriterionResult | None] = {}
        self._sitemap_cache: dict[str, ScoringCriterionResult | None] = {}

    async def score_page(self, page_data: dict) -> list[ScoringCriterionResult]:
        """Score a single page against all 23 authority criteria.

        Args:
            page_data: Dict from CrawlResult.model_dump() with keys:
                url, domain, main_content, html (or main_content as fallback),
                crawl_data, internal_links, schemas, etc.

        Returns:
            List of 23 ScoringCriterionResult instances (A1-A8, S1-S15).
        """
        url = page_data.get("url", "")
        domain = page_data.get("domain", "")
        html = page_data.get("html", page_data.get("main_content", ""))
        crawl_data = page_data
        soup = BeautifulSoup(html, "lxml")

        # Extract schema.org data from crawl_data
        schemas = self._extract_schemas(crawl_data)

        # Extract brand name from crawl data
        brand_name = self._extract_brand_name(crawl_data, soup)

        results: list[ScoringCriterionResult] = []

        # ---- E-E-A-T / Entity Signals (A1-A8) ----

        # A1: Author bios with credentials
        results.append(self._check_author_bios(soup, schemas))

        # A2: Published/modified dates
        results.append(self._check_dates(soup, schemas))

        # A3-A5: External API checks (run concurrently)
        a3_task = self._check_knowledge_graph(domain, brand_name)
        a4_task = self._check_wikidata(brand_name, domain)
        a5_task = self._check_wikipedia(brand_name)
        a3_result, a4_result, a5_result = await asyncio.gather(
            a3_task, a4_task, a5_task
        )
        results.append(a3_result)
        results.append(a4_result)
        results.append(a5_result)

        # A6: Review platform profiles
        results.append(self._check_review_profiles(schemas, soup))

        # A7: Brand search volume signal (proxy)
        results.append(self._check_brand_signal(crawl_data, schemas))

        # A8: E-E-A-T composite score (from A1-A7)
        eeat_results = results[:7]  # A1-A7
        results.append(self._compute_eeat_composite(eeat_results))

        # ---- SEO Fundamentals (S1-S15) ----

        # S1: SSL/HTTPS
        results.append(self._check_ssl(url))

        # S2: Canonical tags
        results.append(self._check_canonical(soup))

        # S3: Meta title optimization
        results.append(self._check_meta_title(soup, crawl_data))

        # S4: Meta description quality
        results.append(self._check_meta_description(soup))

        # S5: XML sitemap presence (async)
        results.append(await self._check_sitemap(domain))

        # S6: Open Graph tags
        results.append(self._check_og_tags(crawl_data))

        # S7: Mobile friendliness
        results.append(self._check_mobile(soup))

        # S8: Internal linking score
        results.append(self._check_internal_links(soup, domain))

        # S9: Backlink profile proxy
        results.append(self._check_backlink_proxy(page_data))

        # S10: Referring domains proxy
        results.append(self._check_referring_domains_proxy(page_data, schemas))

        # S11: Core Web Vitals - LCP (async, homepage only)
        results.append(await self._check_cwv(url))

        # S12: URL structure quality
        results.append(self._check_url_structure(url))

        # S13: Image alt text coverage
        results.append(self._check_alt_text(soup))

        # S14: Broken links
        results.append(self._check_broken_links(soup))

        # S15: Orphan pages detection
        results.append(self._check_orphan_pages(page_data))

        return results

    # ------------------------------------------------------------------
    # Helper: Extract schemas from crawl data
    # ------------------------------------------------------------------

    def _extract_schemas(self, crawl_data: dict) -> list[dict]:
        """Extract JSON-LD schemas from crawl data.

        Args:
            crawl_data: Crawl result dict which may contain schema_org or
                        structured_data fields.

        Returns:
            List of schema dicts found in crawl data.
        """
        schemas = crawl_data.get("schema_org", [])
        if not schemas:
            schemas = crawl_data.get("structured_data", {}).get("json_ld", [])
        if not schemas:
            schemas = crawl_data.get("schemas", [])
        if isinstance(schemas, dict):
            schemas = [schemas]
        return schemas if isinstance(schemas, list) else []

    def _extract_brand_name(self, crawl_data: dict, soup: BeautifulSoup) -> str:
        """Extract brand name from crawl data using priority cascade.

        Priority: schema.org Organization name > og:site_name > title tag > domain.

        Args:
            crawl_data: Crawl result dict.
            soup: Parsed HTML of the page.

        Returns:
            Brand name string.
        """
        # Try schema.org Organization name
        schemas = self._extract_schemas(crawl_data)
        for schema in schemas:
            if schema.get("@type") == "Organization" and schema.get("name"):
                return schema["name"]

        # Try og:site_name
        og_site = crawl_data.get("og_tags", {}).get("og:site_name", "")
        if og_site:
            return og_site

        # Try title tag (take first part before separator)
        title = crawl_data.get("title", "")
        if not title:
            title_tag = soup.find("title")
            title = title_tag.get_text(strip=True) if title_tag else ""
        if title:
            for sep in [" | ", " - ", " :: ", " — ", " – "]:
                if sep in title:
                    parts = title.split(sep)
                    # Brand is usually the last part
                    return parts[-1].strip()
            return title.strip()

        # Fallback: domain
        domain = crawl_data.get("domain", "")
        if domain:
            # Strip www. and TLD
            parts = domain.replace("www.", "").split(".")
            return parts[0].capitalize() if parts else domain
        return ""

    # ------------------------------------------------------------------
    # A1: Author bios with credentials (GRADIENT)
    # ------------------------------------------------------------------

    def _check_author_bios(
        self, soup: BeautifulSoup, schemas: list[dict]
    ) -> ScoringCriterionResult:
        """Check for author information with credentials.

        Detects author info via schema.org Person/author, HTML address/byline
        patterns, and bio sections near author names.

        Args:
            soup: Parsed HTML of the page.
            schemas: List of JSON-LD schemas from the page.

        Returns:
            ScoringCriterionResult with score 0-100.
        """
        author_name = None
        has_credentials = False

        # Check schema.org for author with credentials
        for schema in schemas:
            author = schema.get("author")
            if isinstance(author, dict):
                author_name = author.get("name", "")
                if author.get("jobTitle") or author.get("affiliation"):
                    has_credentials = True
            elif isinstance(author, list):
                for a in author:
                    if isinstance(a, dict) and a.get("name"):
                        author_name = a["name"]
                        if a.get("jobTitle") or a.get("affiliation"):
                            has_credentials = True
                        break

        # Check HTML patterns
        if not author_name:
            # Look for byline patterns
            byline_patterns = [
                r"[Bb]y\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
                r"[Ww]ritten\s+by\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
                r"[Aa]uthor:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
            ]
            text = soup.get_text()
            for pattern in byline_patterns:
                match = re.search(pattern, text)
                if match:
                    author_name = match.group(1)
                    break

            # Check for author-class elements
            if not author_name:
                author_el = soup.find(
                    class_=re.compile(r"author|byline", re.IGNORECASE)
                )
                if author_el:
                    author_name = author_el.get_text(strip=True)

            # Check for <address> with author content
            if not author_name:
                for addr in soup.find_all("address"):
                    addr_text = addr.get_text(strip=True)
                    if addr_text and len(addr_text) > 3:
                        author_name = addr_text
                        break

        # If author found, check for credentials in surrounding context
        if author_name and not has_credentials:
            text = soup.get_text()
            # Look for credential indicators near author name
            credential_patterns = [
                r"(?:PhD|Ph\.D|MD|M\.D|MBA|CTO|CEO|VP|Director|Professor|Dr\.)",
                r"(?:years?\s+(?:of\s+)?experience)",
                r"(?:certified|licensed|accredited)",
            ]
            for pattern in credential_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    has_credentials = True
                    break

        if author_name and has_credentials:
            return ScoringCriterionResult(
                criterion_id="A1",
                criterion_name="Author bios with credentials",
                score=100,
                human_summary=f"Author '{author_name}' identified with credentials -- strong E-E-A-T signal",
                technical_detail=f"Author: {author_name}, credentials detected via schema.org or page content",
                evidence={"author_name": author_name, "has_credentials": True},
            )
        elif author_name:
            return ScoringCriterionResult(
                criterion_id="A1",
                criterion_name="Author bios with credentials",
                score=50,
                human_summary=f"Author '{author_name}' identified but no credentials found",
                technical_detail=f"Author: {author_name}, no jobTitle/affiliation/credential markers detected",
                evidence={"author_name": author_name, "has_credentials": False},
            )
        else:
            return ScoringCriterionResult(
                criterion_id="A1",
                criterion_name="Author bios with credentials",
                score=0,
                human_summary="No author information found -- weak E-E-A-T signal",
                technical_detail="No author detected via schema.org, byline patterns, or HTML classes",
                evidence={"author_name": None, "has_credentials": False},
            )

    # ------------------------------------------------------------------
    # A2: Published/modified dates (GRADIENT)
    # ------------------------------------------------------------------

    def _check_dates(
        self, soup: BeautifulSoup, schemas: list[dict]
    ) -> ScoringCriterionResult:
        """Check for published and modified dates.

        Looks for dates in schema.org, HTML time elements, meta tags,
        and visible date patterns.

        Args:
            soup: Parsed HTML of the page.
            schemas: List of JSON-LD schemas from the page.

        Returns:
            ScoringCriterionResult with score 0-100.
        """
        date_published = None
        date_modified = None
        dates_visible = False

        # Check schema.org
        for schema in schemas:
            if schema.get("datePublished"):
                date_published = str(schema["datePublished"])
            if schema.get("dateModified"):
                date_modified = str(schema["dateModified"])

        # Check <time> elements
        time_els = soup.find_all("time")
        for time_el in time_els:
            dt = time_el.get("datetime", "")
            if dt and not date_published:
                date_published = dt
                dates_visible = True
            elif dt and date_published and not date_modified:
                date_modified = dt
                dates_visible = True

        # Check meta tags
        for name in ["article:published_time", "date", "DC.date.issued"]:
            meta = soup.find("meta", attrs={"property": name}) or soup.find(
                "meta", attrs={"name": name}
            )
            if meta and meta.get("content") and not date_published:
                date_published = meta["content"]

        for name in ["article:modified_time", "DC.date.modified"]:
            meta = soup.find("meta", attrs={"property": name}) or soup.find(
                "meta", attrs={"name": name}
            )
            if meta and meta.get("content") and not date_modified:
                date_modified = meta["content"]

        # Check for visible date patterns in text
        if not dates_visible and (date_published or date_modified):
            # Dates exist in schema/meta but check if visible in page
            text = soup.get_text()
            date_pattern = r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b"
            if re.search(date_pattern, text):
                dates_visible = True

        if date_published and date_modified and dates_visible:
            return ScoringCriterionResult(
                criterion_id="A2",
                criterion_name="Published/modified dates",
                score=100,
                human_summary=f"Published: {date_published}, Modified: {date_modified} -- dates visible to both humans and AI",
                technical_detail=f"datePublished={date_published}, dateModified={date_modified}, visible_in_page={dates_visible}",
                evidence={
                    "date_published": date_published,
                    "date_modified": date_modified,
                    "visible": dates_visible,
                },
            )
        elif date_published and date_modified:
            return ScoringCriterionResult(
                criterion_id="A2",
                criterion_name="Published/modified dates",
                score=70,
                human_summary=f"Both dates present in metadata but may not be visible to users",
                technical_detail=f"datePublished={date_published}, dateModified={date_modified}, visible_in_page={dates_visible}",
                evidence={
                    "date_published": date_published,
                    "date_modified": date_modified,
                    "visible": dates_visible,
                },
            )
        elif date_published:
            return ScoringCriterionResult(
                criterion_id="A2",
                criterion_name="Published/modified dates",
                score=40 if not dates_visible else 70,
                human_summary=f"Published date found ({date_published}) but no modified date",
                technical_detail=f"datePublished={date_published}, no dateModified, visible_in_page={dates_visible}",
                evidence={
                    "date_published": date_published,
                    "date_modified": None,
                    "visible": dates_visible,
                },
            )
        else:
            return ScoringCriterionResult(
                criterion_id="A2",
                criterion_name="Published/modified dates",
                score=0,
                human_summary="No publication dates found -- AI engines prefer dated content for freshness signals",
                technical_detail="No datePublished or dateModified in schema, meta, or visible text",
                evidence={
                    "date_published": None,
                    "date_modified": None,
                    "visible": False,
                },
            )

    # ------------------------------------------------------------------
    # A3: Knowledge Graph presence (GRADIENT)
    # ------------------------------------------------------------------

    async def _check_knowledge_graph(
        self, domain: str, brand_name: str
    ) -> ScoringCriterionResult:
        """Check Google Knowledge Graph for brand/entity presence.

        Calls the Knowledge Graph Search API. Requires GOOGLE_API_KEY.
        If the key is not configured, returns _not_checked.

        Args:
            domain: The website domain.
            brand_name: The brand name to search for.

        Returns:
            ScoringCriterionResult with score 0-100 or not_checked.
        """
        api_key = settings.GOOGLE_API_KEY
        if not api_key:
            return self._not_checked(
                "A3",
                "Knowledge Graph presence",
                "Google API key not configured",
            )

        if not brand_name:
            return self._not_checked(
                "A3",
                "Knowledge Graph presence",
                "Brand name could not be determined",
            )

        try:
            async with self._api_semaphore:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(
                        "https://kgsearch.googleapis.com/v1/entities:search",
                        params={
                            "query": brand_name,
                            "key": api_key,
                            "limit": 3,
                            "indent": True,
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()

            elements = data.get("itemListElement", [])
            if not elements:
                return ScoringCriterionResult(
                    criterion_id="A3",
                    criterion_name="Knowledge Graph presence",
                    score=0,
                    human_summary=f"'{brand_name}' not found in Google Knowledge Graph",
                    technical_detail="No entities returned from Knowledge Graph API",
                    evidence={"brand_name": brand_name, "results_count": 0},
                )

            # Check if any result matches the domain
            domain_match = False
            for element in elements:
                result = element.get("result", {})
                desc_url = (
                    result.get("detailedDescription", {}).get("url", "")
                )
                result_url = result.get("url", "")
                for check_url in [desc_url, result_url]:
                    if check_url and domain in check_url:
                        domain_match = True
                        break
                if domain_match:
                    break

            if domain_match:
                return ScoringCriterionResult(
                    criterion_id="A3",
                    criterion_name="Knowledge Graph presence",
                    score=100,
                    human_summary=f"'{brand_name}' found in Google Knowledge Graph with domain match -- strong entity signal",
                    technical_detail=f"Knowledge Graph entity found matching domain {domain}",
                    evidence={
                        "brand_name": brand_name,
                        "domain_match": True,
                        "results_count": len(elements),
                    },
                )
            else:
                return ScoringCriterionResult(
                    criterion_id="A3",
                    criterion_name="Knowledge Graph presence",
                    score=40,
                    human_summary=f"Entity found in Knowledge Graph but no domain match for '{domain}'",
                    technical_detail=f"Found {len(elements)} results but none matched domain {domain}",
                    evidence={
                        "brand_name": brand_name,
                        "domain_match": False,
                        "results_count": len(elements),
                    },
                )

        except Exception as e:
            logger.warning("Knowledge Graph API error: {}", str(e))
            return self._not_checked(
                "A3",
                "Knowledge Graph presence",
                f"API error: {str(e)[:100]}",
            )

    # ------------------------------------------------------------------
    # A4: Wikidata QID linkage (GRADIENT)
    # ------------------------------------------------------------------

    async def _check_wikidata(
        self, brand_name: str, domain: str
    ) -> ScoringCriterionResult:
        """Check Wikidata for entity presence.

        Searches Wikidata for the brand name and checks if results match.

        Args:
            brand_name: The brand name to search for.
            domain: The website domain for matching.

        Returns:
            ScoringCriterionResult with score 0-100 or not_checked.
        """
        if not brand_name:
            return self._not_checked(
                "A4", "Wikidata QID linkage", "Brand name could not be determined"
            )

        try:
            async with self._api_semaphore:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(
                        "https://www.wikidata.org/w/api.php",
                        params={
                            "action": "wbsearchentities",
                            "search": brand_name,
                            "language": "en",
                            "format": "json",
                            "limit": 5,
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()

            results = data.get("search", [])
            if not results:
                return ScoringCriterionResult(
                    criterion_id="A4",
                    criterion_name="Wikidata QID linkage",
                    score=0,
                    human_summary=f"'{brand_name}' not found on Wikidata -- no structured entity data",
                    technical_detail="No Wikidata entities returned for search",
                    evidence={"brand_name": brand_name, "qid": None},
                )

            # Check if any result has a matching description
            domain_base = domain.replace("www.", "").split(".")[0].lower()
            for result in results:
                qid = result.get("id", "")
                label = result.get("label", "").lower()
                description = result.get("description", "").lower()

                # Check for match: label matches brand or description mentions domain/brand
                if (
                    brand_name.lower() in label
                    or domain_base in description
                    or brand_name.lower() in description
                ):
                    return ScoringCriterionResult(
                        criterion_id="A4",
                        criterion_name="Wikidata QID linkage",
                        score=100,
                        human_summary=f"Wikidata entity {qid} found for '{brand_name}' -- structured knowledge base presence",
                        technical_detail=f"QID={qid}, label='{result.get('label', '')}', description='{result.get('description', '')}'",
                        evidence={
                            "brand_name": brand_name,
                            "qid": qid,
                            "label": result.get("label", ""),
                            "description": result.get("description", ""),
                        },
                    )

            # Results found but uncertain match
            first_qid = results[0].get("id", "")
            return ScoringCriterionResult(
                criterion_id="A4",
                criterion_name="Wikidata QID linkage",
                score=40,
                human_summary=f"Wikidata entities found but uncertain match for '{brand_name}'",
                technical_detail=f"Found {len(results)} results, closest QID={first_qid}",
                evidence={
                    "brand_name": brand_name,
                    "qid": first_qid,
                    "match_confidence": "uncertain",
                },
            )

        except Exception as e:
            logger.warning("Wikidata API error: {}", str(e))
            return self._not_checked(
                "A4",
                "Wikidata QID linkage",
                f"API error: {str(e)[:100]}",
            )

    # ------------------------------------------------------------------
    # A5: Wikipedia page/backlinks (GRADIENT)
    # ------------------------------------------------------------------

    async def _check_wikipedia(self, brand_name: str) -> ScoringCriterionResult:
        """Check Wikipedia for a dedicated page about the brand.

        Args:
            brand_name: The brand name to search for.

        Returns:
            ScoringCriterionResult with score 0-100 or not_checked.
        """
        if not brand_name:
            return self._not_checked(
                "A5",
                "Wikipedia page/backlinks",
                "Brand name could not be determined",
            )

        try:
            async with self._api_semaphore:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(
                        "https://en.wikipedia.org/w/api.php",
                        params={
                            "action": "query",
                            "titles": brand_name,
                            "prop": "extracts",
                            "exintro": True,
                            "format": "json",
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()

            pages = data.get("query", {}).get("pages", {})
            for page_id, page_data in pages.items():
                if page_id == "-1" or page_data.get("missing") is not None:
                    # Also try a search query for broader matching
                    return await self._wikipedia_search(brand_name)

                # Page exists
                extract = page_data.get("extract", "")
                title = page_data.get("title", "")
                return ScoringCriterionResult(
                    criterion_id="A5",
                    criterion_name="Wikipedia page/backlinks",
                    score=100,
                    human_summary=f"Dedicated Wikipedia page found: '{title}' -- strong authority signal for AI engines",
                    technical_detail=f"Wikipedia page exists with title '{title}', extract length: {len(extract)} chars",
                    evidence={
                        "brand_name": brand_name,
                        "wikipedia_title": title,
                        "has_page": True,
                    },
                )

            return ScoringCriterionResult(
                criterion_id="A5",
                criterion_name="Wikipedia page/backlinks",
                score=0,
                human_summary=f"No Wikipedia page found for '{brand_name}'",
                technical_detail="Wikipedia query returned no matching pages",
                evidence={"brand_name": brand_name, "has_page": False},
            )

        except Exception as e:
            logger.warning("Wikipedia API error: {}", str(e))
            return self._not_checked(
                "A5",
                "Wikipedia page/backlinks",
                f"API error: {str(e)[:100]}",
            )

    async def _wikipedia_search(self, brand_name: str) -> ScoringCriterionResult:
        """Fallback Wikipedia search when exact title match fails.

        Args:
            brand_name: The brand name to search for.

        Returns:
            ScoringCriterionResult with score 0 or 50.
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://en.wikipedia.org/w/api.php",
                    params={
                        "action": "query",
                        "list": "search",
                        "srsearch": brand_name,
                        "srlimit": 3,
                        "format": "json",
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            search_results = data.get("query", {}).get("search", [])
            if search_results:
                return ScoringCriterionResult(
                    criterion_id="A5",
                    criterion_name="Wikipedia page/backlinks",
                    score=50,
                    human_summary=f"Brand mentioned in Wikipedia pages but no dedicated page",
                    technical_detail=f"Found {len(search_results)} search results mentioning '{brand_name}'",
                    evidence={
                        "brand_name": brand_name,
                        "has_page": False,
                        "mentioned_in_pages": len(search_results),
                    },
                )
        except Exception:
            pass

        return ScoringCriterionResult(
            criterion_id="A5",
            criterion_name="Wikipedia page/backlinks",
            score=0,
            human_summary=f"No Wikipedia presence found for '{brand_name}'",
            technical_detail="No dedicated page or search mentions found",
            evidence={"brand_name": brand_name, "has_page": False},
        )

    # ------------------------------------------------------------------
    # A6: Review platform profiles (GRADIENT)
    # ------------------------------------------------------------------

    def _check_review_profiles(
        self, schemas: list[dict], soup: BeautifulSoup
    ) -> ScoringCriterionResult:
        """Check for presence on review platforms.

        Looks for links to review platforms in sameAs schema, page links,
        and text content.

        Args:
            schemas: List of JSON-LD schemas from the page.
            soup: Parsed HTML of the page.

        Returns:
            ScoringCriterionResult with score 0-100.
        """
        found_platforms: set[str] = set()

        # Check sameAs in Organization schema
        for schema in schemas:
            same_as = schema.get("sameAs", [])
            if isinstance(same_as, str):
                same_as = [same_as]
            for url in same_as:
                for platform in REVIEW_PLATFORMS:
                    if platform in str(url):
                        found_platforms.add(platform)

        # Check <a> links pointing to review platforms
        for a_tag in soup.find_all("a", href=True):
            href = str(a_tag["href"])
            for platform in REVIEW_PLATFORMS:
                if platform in href:
                    found_platforms.add(platform)

        count = len(found_platforms)
        platforms_list = sorted(found_platforms)

        if count >= 3:
            score = 100
        elif count == 2:
            score = 70
        elif count == 1:
            score = 40
        else:
            score = 0

        if count > 0:
            summary = f"Present on {count} review platform(s) ({', '.join(platforms_list)})"
        else:
            summary = "No review platform profiles detected -- review presence strengthens trust signals"

        return ScoringCriterionResult(
            criterion_id="A6",
            criterion_name="Review platform profiles",
            score=score,
            human_summary=summary,
            technical_detail=f"Found {count} review platforms: {platforms_list}",
            evidence={"platforms": platforms_list, "count": count},
        )

    # ------------------------------------------------------------------
    # A7: Brand search volume signal (GRADIENT, proxy)
    # ------------------------------------------------------------------

    def _check_brand_signal(
        self, crawl_data: dict, schemas: list[dict]
    ) -> ScoringCriterionResult:
        """Check proxy signals for brand search volume.

        Uses proxy signals since actual search volume requires paid APIs:
        branded title, Organization schema strength, social profiles, domain
        indicators.

        Args:
            crawl_data: Crawl result dict.
            schemas: List of JSON-LD schemas.

        Returns:
            ScoringCriterionResult with score 0-80.
        """
        signals: list[str] = []

        # Signal 1: Branded title tag
        title = crawl_data.get("title", "")
        domain = crawl_data.get("domain", "").replace("www.", "")
        domain_base = domain.split(".")[0].lower() if domain else ""
        if title and domain_base and domain_base.lower() in title.lower():
            signals.append("branded_title")

        # Signal 2: Strong Organization schema
        for schema in schemas:
            if schema.get("@type") == "Organization":
                org_fields = ["name", "url", "logo"]
                present = sum(1 for f in org_fields if schema.get(f))
                if present >= 2:
                    signals.append("org_schema")
                break

        # Signal 3: Social profiles linked
        social_domains = [
            "twitter.com",
            "x.com",
            "linkedin.com",
            "facebook.com",
            "instagram.com",
            "github.com",
            "youtube.com",
        ]
        for schema in schemas:
            same_as = schema.get("sameAs", [])
            if isinstance(same_as, str):
                same_as = [same_as]
            social_count = sum(
                1
                for url in same_as
                if any(sd in str(url) for sd in social_domains)
            )
            if social_count >= 2:
                signals.append("social_profiles")
                break

        # Signal 4: Domain age indicators (heuristic: has copyright year in page)
        html = crawl_data.get("main_content", "")
        copyright_match = re.search(
            r"(?:\u00a9|&copy;|copyright)\s*(\d{4})", html, re.IGNORECASE
        )
        if copyright_match:
            try:
                year = int(copyright_match.group(1))
                if year <= 2020:  # At least a few years old
                    signals.append("domain_age")
            except ValueError:
                pass

        signal_count = len(signals)
        score_map = {0: 0, 1: 20, 2: 40, 3: 60, 4: 80}
        score = score_map.get(signal_count, 80)

        return ScoringCriterionResult(
            criterion_id="A7",
            criterion_name="Brand search volume signal",
            score=score,
            human_summary=f"{signal_count} brand presence signal(s) detected: {', '.join(signals) if signals else 'none'}",
            technical_detail="Proxy signal -- actual brand search volume requires third-party data",
            evidence={"signals": signals, "count": signal_count},
        )

    # ------------------------------------------------------------------
    # A8: E-E-A-T composite score (GRADIENT)
    # ------------------------------------------------------------------

    def _compute_eeat_composite(
        self, results: list[ScoringCriterionResult]
    ) -> ScoringCriterionResult:
        """Compute composite E-E-A-T score from A1-A7.

        Averages only checked criteria scores.

        Args:
            results: List of A1-A7 ScoringCriterionResult instances.

        Returns:
            ScoringCriterionResult representing the E-E-A-T composite.
        """
        checked = [r for r in results if r.checked]
        if not checked:
            return self._not_checked(
                "A8",
                "E-E-A-T composite score",
                "No E-E-A-T criteria could be checked",
            )

        avg_score = round(sum(r.score for r in checked) / len(checked))
        return ScoringCriterionResult(
            criterion_id="A8",
            criterion_name="E-E-A-T composite score",
            score=avg_score,
            human_summary=f"E-E-A-T composite: {avg_score}/100 based on {len(checked)} signals checked",
            technical_detail=f"Average of {len(checked)} checked criteria (A1-A7): {[r.criterion_id + '=' + str(r.score) for r in checked]}",
            evidence={
                "checked_count": len(checked),
                "total_count": len(results),
                "component_scores": {
                    r.criterion_id: r.score for r in checked
                },
            },
        )

    # ------------------------------------------------------------------
    # S1: SSL/HTTPS (BINARY)
    # ------------------------------------------------------------------

    def _check_ssl(self, url: str) -> ScoringCriterionResult:
        """Check if the URL uses HTTPS.

        Args:
            url: Page URL.

        Returns:
            ScoringCriterionResult (binary: 100 or 0).
        """
        is_ssl = url.startswith("https://")
        return ScoringCriterionResult(
            criterion_id="S1",
            criterion_name="SSL/HTTPS",
            score=100 if is_ssl else 0,
            is_binary=True,
            human_summary="HTTPS enabled -- secure connection" if is_ssl else "No HTTPS -- insecure site penalized by all search engines",
            technical_detail=f"URL scheme: {'https' if is_ssl else 'http'}",
            evidence={"url": url, "is_ssl": is_ssl},
        )

    # ------------------------------------------------------------------
    # S2: Canonical tags (BINARY)
    # ------------------------------------------------------------------

    def _check_canonical(self, soup: BeautifulSoup) -> ScoringCriterionResult:
        """Check for a canonical link tag.

        Args:
            soup: Parsed HTML of the page.

        Returns:
            ScoringCriterionResult (binary: 100 or 0).
        """
        canonical = soup.find("link", rel="canonical")
        has_canonical = canonical is not None and canonical.get("href")
        href = canonical.get("href", "") if canonical else ""

        return ScoringCriterionResult(
            criterion_id="S2",
            criterion_name="Canonical tags",
            score=100 if has_canonical else 0,
            is_binary=True,
            human_summary="Canonical tag present -- prevents duplicate content issues" if has_canonical else "No canonical tag -- risks duplicate content in AI indexes",
            technical_detail=f"<link rel='canonical' href='{href}'>" if has_canonical else "No <link rel='canonical'> found",
            evidence={"has_canonical": has_canonical, "href": href},
        )

    # ------------------------------------------------------------------
    # S3: Meta title optimization (GRADIENT)
    # ------------------------------------------------------------------

    def _check_meta_title(
        self, soup: BeautifulSoup, crawl_data: dict
    ) -> ScoringCriterionResult:
        """Check title tag quality (exists, length, brand inclusion).

        Optimal title: 50-60 chars, contains brand name.

        Args:
            soup: Parsed HTML of the page.
            crawl_data: Crawl result dict.

        Returns:
            ScoringCriterionResult with score 0-100.
        """
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else ""

        if not title:
            return ScoringCriterionResult(
                criterion_id="S3",
                criterion_name="Meta title optimization",
                score=0,
                human_summary="Missing title tag -- critical SEO element",
                technical_detail="No <title> element found",
                evidence={"title": None, "length": 0},
            )

        length = len(title)
        domain = crawl_data.get("domain", "").replace("www.", "")
        domain_base = domain.split(".")[0].lower() if domain else ""
        has_brand = domain_base and domain_base.lower() in title.lower()

        # Score: optimal length (50-60) + brand = 100
        if 50 <= length <= 60 and has_brand:
            score = 100
            summary = f"Optimal title ({length} chars) with brand name"
        elif 30 <= length <= 70 and has_brand:
            score = 80
            summary = f"Good title ({length} chars) with brand name"
        elif 30 <= length <= 70:
            score = 60
            summary = f"Acceptable title length ({length} chars) but no brand name"
        elif has_brand:
            score = 50
            summary = f"Brand in title but suboptimal length ({length} chars, ideal: 50-60)"
        else:
            score = 30
            summary = f"Title exists but suboptimal ({length} chars, no brand)"

        return ScoringCriterionResult(
            criterion_id="S3",
            criterion_name="Meta title optimization",
            score=score,
            human_summary=summary,
            technical_detail=f"Title: '{title[:80]}', length={length}, has_brand={has_brand}",
            evidence={
                "title": title[:200],
                "length": length,
                "has_brand": has_brand,
            },
        )

    # ------------------------------------------------------------------
    # S4: Meta description quality (GRADIENT)
    # ------------------------------------------------------------------

    def _check_meta_description(
        self, soup: BeautifulSoup
    ) -> ScoringCriterionResult:
        """Check meta description quality (exists, length).

        Optimal description: 150-160 chars.

        Args:
            soup: Parsed HTML of the page.

        Returns:
            ScoringCriterionResult with score 0-100.
        """
        meta = soup.find("meta", attrs={"name": "description"})
        description = meta.get("content", "").strip() if meta else ""

        if not description:
            return ScoringCriterionResult(
                criterion_id="S4",
                criterion_name="Meta description quality",
                score=0,
                human_summary="Missing meta description -- missed opportunity for AI context",
                technical_detail="No <meta name='description'> found",
                evidence={"description": None, "length": 0},
            )

        length = len(description)
        if 150 <= length <= 160:
            score = 100
            summary = f"Optimal meta description ({length} chars)"
        elif 120 <= length <= 200:
            score = 70
            summary = f"Good meta description ({length} chars, ideal: 150-160)"
        elif 50 <= length <= 300:
            score = 50
            summary = f"Meta description exists but suboptimal length ({length} chars)"
        else:
            score = 30
            summary = f"Meta description too {'short' if length < 50 else 'long'} ({length} chars)"

        return ScoringCriterionResult(
            criterion_id="S4",
            criterion_name="Meta description quality",
            score=score,
            human_summary=summary,
            technical_detail=f"Description: '{description[:100]}...', length={length}",
            evidence={"description": description[:300], "length": length},
        )

    # ------------------------------------------------------------------
    # S5: XML sitemap presence (BINARY, async)
    # ------------------------------------------------------------------

    async def _check_sitemap(self, domain: str) -> ScoringCriterionResult:
        """Check for XML sitemap at /sitemap.xml.

        Caches result per domain to avoid repeated requests.

        Args:
            domain: The website domain.

        Returns:
            ScoringCriterionResult (binary: 100 or 0).
        """
        if domain in self._sitemap_cache:
            return self._sitemap_cache[domain]

        sitemap_url = f"https://{domain}/sitemap.xml"
        try:
            async with self._api_semaphore:
                async with httpx.AsyncClient(
                    timeout=10.0, follow_redirects=True
                ) as client:
                    resp = await client.head(sitemap_url)
                    found = resp.status_code == 200
        except Exception:
            found = False

        result = ScoringCriterionResult(
            criterion_id="S5",
            criterion_name="XML sitemap presence",
            score=100 if found else 0,
            is_binary=True,
            human_summary="XML sitemap found -- helps AI crawlers discover your content" if found else "No XML sitemap at /sitemap.xml -- AI crawlers may miss pages",
            technical_detail=f"HEAD {sitemap_url} -> {'200' if found else 'not found'}",
            evidence={"sitemap_url": sitemap_url, "found": found},
        )
        self._sitemap_cache[domain] = result
        return result

    # ------------------------------------------------------------------
    # S6: Open Graph tags (GRADIENT)
    # ------------------------------------------------------------------

    def _check_og_tags(self, crawl_data: dict) -> ScoringCriterionResult:
        """Check Open Graph tag completeness.

        Checks for og:title, og:description, og:image, og:type, og:url.

        Args:
            crawl_data: Crawl result dict.

        Returns:
            ScoringCriterionResult with score 0-100.
        """
        og_tags = crawl_data.get("og_tags", {})
        required_tags = ["og:title", "og:description", "og:image", "og:type", "og:url"]
        present = [tag for tag in required_tags if og_tags.get(tag)]
        missing = [tag for tag in required_tags if not og_tags.get(tag)]

        count = len(present)
        score = count * 20  # 0-100 in steps of 20

        if count == 5:
            summary = "All 5 Open Graph tags present -- optimal social/AI sharing"
        elif count >= 3:
            summary = f"{count}/5 OG tags present, missing: {', '.join(missing)}"
        elif count > 0:
            summary = f"Only {count}/5 OG tags found -- incomplete social metadata"
        else:
            summary = "No Open Graph tags found -- poor social/AI sharing signals"

        return ScoringCriterionResult(
            criterion_id="S6",
            criterion_name="Open Graph tags",
            score=score,
            human_summary=summary,
            technical_detail=f"Present: {present}, Missing: {missing}",
            evidence={"present": present, "missing": missing, "count": count},
        )

    # ------------------------------------------------------------------
    # S7: Mobile friendliness (GRADIENT)
    # ------------------------------------------------------------------

    def _check_mobile(self, soup: BeautifulSoup) -> ScoringCriterionResult:
        """Check for mobile-friendly design indicators.

        Checks viewport meta tag and responsive design patterns.

        Args:
            soup: Parsed HTML of the page.

        Returns:
            ScoringCriterionResult with score 0-100.
        """
        # Check viewport meta tag
        viewport = soup.find("meta", attrs={"name": "viewport"})
        has_viewport = viewport is not None
        viewport_content = viewport.get("content", "") if viewport else ""

        # Check for responsive indicators
        responsive = False
        if has_viewport:
            # Good viewport should have width=device-width
            if "width=device-width" in viewport_content:
                responsive = True

        # Check for fixed-width indicators (anti-pattern)
        fixed_width = False
        style_tags = soup.find_all("style")
        for style in style_tags:
            text = style.get_text()
            if re.search(r"width:\s*\d{3,4}px", text):
                fixed_width = True
                break

        if has_viewport and responsive and not fixed_width:
            score = 100
            summary = "Mobile-friendly: viewport meta tag with responsive design"
        elif has_viewport:
            score = 60
            summary = "Viewport tag present but responsive design uncertain"
        else:
            score = 0
            summary = "No viewport meta tag -- not mobile-friendly"

        return ScoringCriterionResult(
            criterion_id="S7",
            criterion_name="Mobile friendliness",
            score=score,
            human_summary=summary,
            technical_detail=f"Viewport: {viewport_content}, responsive={responsive}, fixed_width={fixed_width}",
            evidence={
                "has_viewport": has_viewport,
                "viewport_content": viewport_content,
                "responsive": responsive,
                "fixed_width": fixed_width,
            },
        )

    # ------------------------------------------------------------------
    # S8: Internal linking score (GRADIENT)
    # ------------------------------------------------------------------

    def _check_internal_links(
        self, soup: BeautifulSoup, domain: str
    ) -> ScoringCriterionResult:
        """Count internal links on the page.

        Args:
            soup: Parsed HTML of the page.
            domain: The website domain for filtering.

        Returns:
            ScoringCriterionResult with score 0-100.
        """
        internal_count = 0
        for a_tag in soup.find_all("a", href=True):
            href = str(a_tag["href"])
            # Internal link: relative path or same domain
            if href.startswith("/") and not href.startswith("//"):
                internal_count += 1
            elif domain and domain in href:
                internal_count += 1

        if internal_count >= 20:
            score = 100
        elif internal_count >= 10:
            score = 70
        elif internal_count >= 5:
            score = 40
        elif internal_count >= 1:
            score = 20
        else:
            score = 0

        return ScoringCriterionResult(
            criterion_id="S8",
            criterion_name="Internal linking score",
            score=score,
            human_summary=f"{internal_count} internal links found on this page",
            technical_detail=f"internal_link_count={internal_count}, domain={domain}",
            evidence={"internal_link_count": internal_count},
        )

    # ------------------------------------------------------------------
    # S9: Backlink profile proxy (GRADIENT)
    # ------------------------------------------------------------------

    def _check_backlink_proxy(
        self, page_data: dict
    ) -> ScoringCriterionResult:
        """Estimate backlink profile using proxy signals.

        Uses internal link count, sameAs link count, and outbound links to
        authoritative domains as proxy signals.

        Args:
            page_data: Crawl result dict.

        Returns:
            ScoringCriterionResult with score 0-100.
        """
        # Signal 1: Internal links to this page
        internal_link_count = page_data.get("internal_link_count", 0)

        # Signal 2: sameAs links count from Organization schema
        schemas = self._extract_schemas(page_data)
        same_as_count = 0
        for schema in schemas:
            same_as = schema.get("sameAs", [])
            if isinstance(same_as, str):
                same_as = [same_as]
            same_as_count += len(same_as)

        # Signal 3: Outbound links to authoritative domains
        html = page_data.get("html", page_data.get("main_content", ""))
        soup = BeautifulSoup(html, "lxml")
        authority_count = 0
        for a_tag in soup.find_all("a", href=True):
            href = str(a_tag["href"])
            for auth_domain in AUTHORITATIVE_DOMAINS:
                if auth_domain in href:
                    authority_count += 1
                    break

        # Composite score from three signals
        signal_score = 0
        if internal_link_count >= 5:
            signal_score += 40
        elif internal_link_count >= 2:
            signal_score += 25
        elif internal_link_count >= 1:
            signal_score += 10

        if same_as_count >= 3:
            signal_score += 30
        elif same_as_count >= 1:
            signal_score += 15

        if authority_count >= 3:
            signal_score += 30
        elif authority_count >= 1:
            signal_score += 15

        score = min(100, signal_score)

        return ScoringCriterionResult(
            criterion_id="S9",
            criterion_name="Backlink profile proxy",
            score=score,
            human_summary=f"Backlink proxy: {internal_link_count} internal links, {same_as_count} sameAs, {authority_count} authority outlinks",
            technical_detail="Proxy signal -- real DR/DA requires paid API (Ahrefs/Moz)",
            evidence={
                "internal_link_count": internal_link_count,
                "same_as_count": same_as_count,
                "authority_outlink_count": authority_count,
            },
        )

    # ------------------------------------------------------------------
    # S10: Referring domains proxy (GRADIENT)
    # ------------------------------------------------------------------

    def _check_referring_domains_proxy(
        self, page_data: dict, schemas: list[dict]
    ) -> ScoringCriterionResult:
        """Estimate referring domain diversity using proxy signals.

        Uses sameAs platform count and external link domain diversity.

        Args:
            page_data: Crawl result dict.
            schemas: List of JSON-LD schemas.

        Returns:
            ScoringCriterionResult with score 0-100.
        """
        # Signal 1: sameAs platforms (proxy for web presence breadth)
        platforms: set[str] = set()
        for schema in schemas:
            same_as = schema.get("sameAs", [])
            if isinstance(same_as, str):
                same_as = [same_as]
            for url in same_as:
                try:
                    parsed = urlparse(str(url))
                    if parsed.netloc:
                        platforms.add(parsed.netloc)
                except Exception:
                    pass

        # Signal 2: Unique external link domains on the page
        html = page_data.get("html", page_data.get("main_content", ""))
        domain = page_data.get("domain", "")
        soup = BeautifulSoup(html, "lxml")
        external_domains: set[str] = set()
        for a_tag in soup.find_all("a", href=True):
            href = str(a_tag["href"])
            try:
                parsed = urlparse(href)
                if parsed.netloc and parsed.netloc != domain:
                    external_domains.add(parsed.netloc)
            except Exception:
                pass

        total_diversity = len(platforms) + len(external_domains)

        if total_diversity >= 10:
            score = 100
        elif total_diversity >= 7:
            score = 80
        elif total_diversity >= 4:
            score = 60
        elif total_diversity >= 2:
            score = 40
        elif total_diversity >= 1:
            score = 20
        else:
            score = 0

        return ScoringCriterionResult(
            criterion_id="S10",
            criterion_name="Referring domains proxy",
            score=score,
            human_summary=f"Domain diversity: {len(platforms)} sameAs platforms, {len(external_domains)} external link domains",
            technical_detail="Proxy signal -- real referring domain count requires paid API",
            evidence={
                "same_as_platforms": list(platforms),
                "external_domains_count": len(external_domains),
                "total_diversity": total_diversity,
            },
        )

    # ------------------------------------------------------------------
    # S11: Core Web Vitals - LCP (GRADIENT, async)
    # ------------------------------------------------------------------

    async def _check_cwv(self, url: str) -> ScoringCriterionResult:
        """Check Core Web Vitals via Google PageSpeed Insights API.

        Only calls PageSpeed for the homepage (first page) to respect rate limits.
        Caches result per domain for all subsequent pages.

        Args:
            url: Page URL.

        Returns:
            ScoringCriterionResult with score 0-100 or not_checked.
        """
        parsed = urlparse(url)
        domain = parsed.netloc

        # Check cache -- only call PageSpeed for first page per domain
        if domain in self._cwv_cache:
            cached = self._cwv_cache[domain]
            if cached is not None:
                return cached
            else:
                return self._not_checked(
                    "S11",
                    "Core Web Vitals (LCP)",
                    "PageSpeed API previously failed for this domain",
                )

        # Build API URL (works with or without API key)
        api_url = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
        params: dict = {
            "url": url,
            "category": "performance",
            "strategy": "mobile",
        }
        if settings.GOOGLE_API_KEY:
            params["key"] = settings.GOOGLE_API_KEY

        try:
            async with self._api_semaphore:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.get(api_url, params=params)
                    resp.raise_for_status()
                    data = resp.json()

            # Extract LCP
            lcp_ms = (
                data.get("lighthouseResult", {})
                .get("audits", {})
                .get("largest-contentful-paint", {})
                .get("numericValue", None)
            )

            if lcp_ms is None:
                self._cwv_cache[domain] = None
                return self._not_checked(
                    "S11",
                    "Core Web Vitals (LCP)",
                    "PageSpeed API did not return LCP data",
                )

            lcp_seconds = lcp_ms / 1000

            # Score: LCP <2.5s = 100, 2.5-4s = linear 50-100, >4s = linear 0-50
            if lcp_seconds <= 2.5:
                score = 100
            elif lcp_seconds <= 4.0:
                # Linear interpolation: 2.5s -> 100, 4.0s -> 50
                score = round(100 - (lcp_seconds - 2.5) / 1.5 * 50)
            else:
                # Linear interpolation: 4.0s -> 50, 8.0s -> 0
                score = max(0, round(50 - (lcp_seconds - 4.0) / 4.0 * 50))

            result = ScoringCriterionResult(
                criterion_id="S11",
                criterion_name="Core Web Vitals (LCP)",
                score=score,
                human_summary=f"LCP: {lcp_seconds:.1f}s {'(Good)' if lcp_seconds <= 2.5 else '(Needs Improvement)' if lcp_seconds <= 4.0 else '(Poor)'}",
                technical_detail=f"Largest Contentful Paint: {lcp_ms:.0f}ms via PageSpeed Insights (mobile)",
                evidence={
                    "lcp_ms": lcp_ms,
                    "lcp_seconds": lcp_seconds,
                    "strategy": "mobile",
                },
            )
            self._cwv_cache[domain] = result
            return result

        except Exception as e:
            logger.warning("PageSpeed API error for {}: {}", url, str(e))
            self._cwv_cache[domain] = None
            return self._not_checked(
                "S11",
                "Core Web Vitals (LCP)",
                f"PageSpeed API error: {str(e)[:100]}",
            )

    # ------------------------------------------------------------------
    # S12: URL structure quality (GRADIENT)
    # ------------------------------------------------------------------

    def _check_url_structure(self, url: str) -> ScoringCriterionResult:
        """Check URL structure quality.

        Evaluates: no query params, lowercase, no special chars, readable words,
        reasonable depth (<4 levels).

        Args:
            url: Page URL.

        Returns:
            ScoringCriterionResult with score 0-100.
        """
        parsed = urlparse(url)
        path = parsed.path
        violations: list[str] = []

        # Check for query parameters
        if parsed.query:
            violations.append("has query parameters")

        # Check for uppercase
        if path != path.lower():
            violations.append("contains uppercase characters")

        # Check for special characters (underscores are debatable, allow hyphens)
        if re.search(r"[^a-zA-Z0-9/\-._~]", path):
            violations.append("contains special characters")

        # Check depth (number of path segments)
        segments = [s for s in path.split("/") if s]
        if len(segments) > 4:
            violations.append(f"deep nesting ({len(segments)} levels)")

        # Check for file extensions in path (except common ones)
        if re.search(r"\.(php|asp|aspx|jsp|cgi)\b", path, re.IGNORECASE):
            violations.append("exposes server technology in URL")

        # Check for IDs/numbers in path
        if re.search(r"/\d{5,}/", path):
            violations.append("contains long numeric IDs")

        violation_count = len(violations)
        if violation_count == 0:
            score = 100
            summary = "Clean URL structure -- readable and search-engine friendly"
        elif violation_count == 1:
            score = 70
            summary = f"Minor URL issue: {violations[0]}"
        elif violation_count == 2:
            score = 40
            summary = f"URL structure issues: {', '.join(violations)}"
        else:
            score = 20
            summary = f"Poor URL structure with {violation_count} issues"

        return ScoringCriterionResult(
            criterion_id="S12",
            criterion_name="URL structure quality",
            score=score,
            human_summary=summary,
            technical_detail=f"URL path: '{path}', violations: {violations}",
            evidence={
                "url": url,
                "violations": violations,
                "depth": len(segments),
            },
        )

    # ------------------------------------------------------------------
    # S13: Image alt text coverage (GRADIENT)
    # ------------------------------------------------------------------

    def _check_alt_text(self, soup: BeautifulSoup) -> ScoringCriterionResult:
        """Check image alt text coverage.

        Counts images with and without alt attributes. Excludes decorative
        images (role="presentation", alt="").

        Args:
            soup: Parsed HTML of the page.

        Returns:
            ScoringCriterionResult with score 0-100.
        """
        images = soup.find_all("img")
        if not images:
            return ScoringCriterionResult(
                criterion_id="S13",
                criterion_name="Image alt text coverage",
                score=100,
                human_summary="No images on page -- no alt text needed",
                technical_detail="0 <img> elements found",
                evidence={"total_images": 0, "with_alt": 0, "coverage": 1.0},
            )

        total = 0
        with_alt = 0
        for img in images:
            # Exclude decorative images
            if img.get("role") == "presentation":
                continue
            alt = img.get("alt")
            if alt == "":
                # Explicitly empty alt = decorative (intentional)
                continue
            total += 1
            if alt is not None and alt.strip():
                with_alt += 1

        if total == 0:
            return ScoringCriterionResult(
                criterion_id="S13",
                criterion_name="Image alt text coverage",
                score=100,
                human_summary="All images are decorative -- no alt text needed",
                technical_detail=f"{len(images)} images found, all decorative (role=presentation or alt='')",
                evidence={
                    "total_images": len(images),
                    "content_images": 0,
                    "coverage": 1.0,
                },
            )

        coverage = with_alt / total
        score = round(coverage * 100)

        if coverage == 1.0:
            summary = f"All {total} content images have alt text"
        elif coverage >= 0.8:
            summary = f"{with_alt}/{total} images have alt text ({score}% coverage)"
        else:
            summary = f"Low alt text coverage: {with_alt}/{total} images ({score}%)"

        return ScoringCriterionResult(
            criterion_id="S13",
            criterion_name="Image alt text coverage",
            score=score,
            human_summary=summary,
            technical_detail=f"total_images={len(images)}, content_images={total}, with_alt={with_alt}",
            evidence={
                "total_images": len(images),
                "content_images": total,
                "with_alt": with_alt,
                "coverage": coverage,
            },
        )

    # ------------------------------------------------------------------
    # S14: Broken links (GRADIENT)
    # ------------------------------------------------------------------

    def _check_broken_links(self, soup: BeautifulSoup) -> ScoringCriterionResult:
        """Check for obviously broken link patterns.

        Does NOT make HTTP requests (too expensive). Instead checks for
        common broken patterns: href="#", empty href, javascript:void.

        Args:
            soup: Parsed HTML of the page.

        Returns:
            ScoringCriterionResult with score 0-100.
        """
        suspicious_count = 0
        suspicious_patterns: list[str] = []

        for a_tag in soup.find_all("a", href=True):
            href = str(a_tag["href"]).strip()
            text = a_tag.get_text(strip=True)

            # Skip anchor-only links that are navigation (no text or generic)
            if href == "#" and text and text.lower() not in (
                "top",
                "back to top",
                "skip to content",
                "skip",
            ):
                suspicious_count += 1
                if len(suspicious_patterns) < 5:
                    suspicious_patterns.append(f'href="#" text="{text[:30]}"')
            elif href == "" or href == "javascript:void(0)" or href == "javascript:;":
                suspicious_count += 1
                if len(suspicious_patterns) < 5:
                    suspicious_patterns.append(f'href="{href}" text="{text[:30]}"')

        if suspicious_count == 0:
            score = 100
        elif suspicious_count <= 2:
            score = 70
        elif suspicious_count <= 5:
            score = 40
        else:
            score = 10

        return ScoringCriterionResult(
            criterion_id="S14",
            criterion_name="Broken links",
            score=score,
            human_summary=f"{suspicious_count} suspicious link pattern(s) detected" if suspicious_count > 0 else "No broken link patterns detected",
            technical_detail=f"Checked for href='#', empty href, javascript:void. Found: {suspicious_patterns}",
            evidence={
                "suspicious_count": suspicious_count,
                "patterns": suspicious_patterns,
            },
        )

    # ------------------------------------------------------------------
    # S15: Orphan pages detection (GRADIENT)
    # ------------------------------------------------------------------

    def _check_orphan_pages(
        self, page_data: dict
    ) -> ScoringCriterionResult:
        """Check if the current page is linked from other pages.

        Uses internal_link_count from the orchestrator's link discovery.

        Args:
            page_data: Crawl result dict with internal_link_count.

        Returns:
            ScoringCriterionResult with score 0-100.
        """
        link_count = page_data.get("internal_link_count", 0)

        if link_count >= 5:
            score = 100
            summary = f"Well-connected page: {link_count} internal links pointing here"
        elif link_count >= 2:
            score = 70
            summary = f"Moderately linked: {link_count} internal links pointing here"
        elif link_count >= 1:
            score = 40
            summary = f"Weakly linked: only {link_count} internal link pointing here"
        else:
            score = 0
            summary = "Orphan page: no internal links pointing here -- may be invisible to AI crawlers"

        return ScoringCriterionResult(
            criterion_id="S15",
            criterion_name="Orphan pages detection",
            score=score,
            human_summary=summary,
            technical_detail=f"internal_link_count={link_count}",
            evidence={"internal_link_count": link_count},
        )
