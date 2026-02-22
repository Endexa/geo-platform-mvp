"""CrawlerService -- extracts AI-readiness signals from a URL.

Fetches a page, parses structured data (JSON-LD, Open Graph, microdata),
checks robots.txt for AI bot directives, and extracts content structure
(headings, main content, keywords, industry signals, authority markers).

Supports multi-page crawling via crawl_multiple() for scoring pipeline.
"""

import asyncio
import logging
import re
from collections import Counter
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

from app.schemas.crawl import AIBotAccess, CrawlResult

try:
    import extruct
    from w3lib.html import get_base_url
except ImportError:
    extruct = None  # type: ignore[assignment]
    get_base_url = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# AI bot user-agents to check in robots.txt
AI_BOTS: dict[str, str] = {
    "GPTBot": "gptbot",
    "ChatGPT-User": "chatgpt_user",
    "ClaudeBot": "claudebot",
    "Claude-SearchBot": "claude_searchbot",
    "PerplexityBot": "perplexitybot",
    "Google-Extended": "google_extended",
    "Applebot-Extended": "applebot_extended",
    "CCBot": "ccbot",
}

MAX_CONTENT_WORDS = 2000

USER_AGENT = "GEOBot/1.0 (+https://geo-platform.com/bot)"

# Common English stopwords for keyword extraction
STOPWORDS = frozenset({
    "the", "be", "to", "of", "and", "a", "in", "that", "have", "i",
    "it", "for", "not", "on", "with", "he", "as", "you", "do", "at",
    "this", "but", "his", "by", "from", "they", "we", "say", "her",
    "she", "or", "an", "will", "my", "one", "all", "would", "there",
    "their", "what", "so", "up", "out", "if", "about", "who", "get",
    "which", "go", "me", "when", "make", "can", "like", "time", "no",
    "just", "him", "know", "take", "people", "into", "year", "your",
    "good", "some", "could", "them", "see", "other", "than", "then",
    "now", "look", "only", "come", "its", "over", "think", "also",
    "back", "after", "use", "two", "how", "our", "work", "first",
    "well", "way", "even", "new", "want", "because", "any", "these",
    "give", "day", "most", "us", "are", "was", "is", "has", "had",
    "been", "were", "more", "very", "may", "own", "such", "should",
    "did", "each", "much", "does", "many", "being", "same", "where",
    "those", "still", "here", "through", "both", "between", "too",
})

# Schema.org types mapped to industry strings
SCHEMA_INDUSTRY_MAP: dict[str, str] = {
    "LocalBusiness": "local-business",
    "Restaurant": "restaurant",
    "FoodEstablishment": "restaurant",
    "MedicalBusiness": "healthcare",
    "MedicalClinic": "healthcare",
    "Hospital": "healthcare",
    "Physician": "healthcare",
    "Dentist": "healthcare",
    "LegalService": "legal",
    "Attorney": "legal",
    "FinancialService": "finance",
    "BankOrCreditUnion": "finance",
    "InsuranceAgency": "finance",
    "RealEstateAgent": "real-estate",
    "RealEstateListing": "real-estate",
    "SoftwareApplication": "software",
    "WebApplication": "software",
    "Store": "retail",
    "OnlineStore": "retail",
    "ShoppingCenter": "retail",
    "EducationalOrganization": "education",
    "School": "education",
    "TravelAgency": "travel",
    "Hotel": "travel",
    "LodgingBusiness": "travel",
    "AutoDealer": "automotive",
    "AutoRepair": "automotive",
}

# Industry keyword lists for heuristic detection
INDUSTRY_KEYWORDS: dict[str, list[str]] = {
    "healthcare": ["health", "medical", "doctor", "patient", "clinic", "hospital", "treatment", "diagnosis"],
    "legal": ["attorney", "lawyer", "legal", "law", "court", "litigation", "contract"],
    "finance": ["finance", "banking", "investment", "insurance", "mortgage", "loan", "credit"],
    "real-estate": ["real estate", "property", "listing", "realtor", "mortgage", "housing"],
    "software": ["software", "saas", "api", "developer", "platform", "cloud", "app"],
    "restaurant": ["restaurant", "menu", "dining", "cuisine", "chef", "reservation"],
    "retail": ["shop", "store", "buy", "product", "cart", "shipping", "retail"],
    "education": ["education", "course", "student", "learning", "university", "school"],
    "travel": ["travel", "hotel", "booking", "flight", "destination", "vacation"],
}


class CrawlerService:
    """Crawls a URL and extracts AI-readiness signals."""

    async def crawl_multiple(
        self,
        start_url: str,
        urls: list[str],
        max_concurrent: int = 5,
    ) -> list[CrawlResult]:
        """Crawl multiple URLs concurrently with controlled parallelism.

        Args:
            start_url: The initial URL (already crawled, for reference only).
            urls: Additional URLs to crawl.
            max_concurrent: Maximum concurrent crawl requests.

        Returns:
            List of CrawlResult for successfully crawled URLs.
            URLs that fail are logged and skipped (graceful degradation).
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        results: list[CrawlResult] = []

        async def _crawl_one(url: str) -> CrawlResult | None:
            async with semaphore:
                try:
                    return await self.crawl(url)
                except Exception as e:
                    logger.warning(
                        "Failed to crawl %s: %s (skipping)", url, str(e)
                    )
                    return None

        tasks = [_crawl_one(url) for url in urls]
        completed = await asyncio.gather(*tasks)
        for result in completed:
            if result is not None:
                results.append(result)

        return results

    async def crawl(self, url: str) -> CrawlResult:
        """Fetch a URL and extract structured AI-readiness signals.

        Args:
            url: The URL to crawl and analyze.

        Returns:
            CrawlResult with all extracted signals.

        Raises:
            httpx.HTTPStatusError: If the HTTP response indicates an error.
            httpx.RequestError: If the request fails (timeout, DNS, etc.).
        """
        async with httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=True,
            max_redirects=5,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

        html = response.text
        soup = BeautifulSoup(html, "lxml")
        parsed_url = urlparse(url)
        domain = parsed_url.netloc

        # Extract structured data (JSON-LD, OG, microdata)
        structured = self._extract_structured_data(html, url)

        # Strip non-content elements before text extraction
        content_soup = BeautifulSoup(html, "lxml")
        for tag in content_soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()

        main_content = self._extract_main_content(content_soup)
        word_count = len(main_content.split())
        keywords = self._extract_keywords(main_content)

        base_url = f"{parsed_url.scheme}://{domain}"
        ai_bot_access = self._check_ai_bot_access(base_url, url)

        schema_org = structured.get("json_ld", [])

        return CrawlResult(
            url=url,
            domain=domain,
            title=self._extract_title(soup),
            meta_description=self._extract_meta_description(soup),
            main_content=main_content,
            headings=self._extract_headings(soup),
            schema_org=schema_org,
            open_graph=self._extract_open_graph(structured),
            microdata=structured.get("microdata", []),
            ai_bot_access=ai_bot_access,
            word_count=word_count,
            content_keywords=keywords,
            industry_signals=self._detect_industry_signals(schema_org, keywords),
            authority_markers=self._extract_authority_markers(soup),
        )

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract the page title from <title> tag."""
        if soup.title and soup.title.string:
            return soup.title.get_text(strip=True)
        return ""

    def _extract_meta_description(self, soup: BeautifulSoup) -> str:
        """Extract the meta description content."""
        meta = soup.find("meta", attrs={"name": "description"})
        if meta and meta.get("content"):
            return meta["content"].strip()
        return ""

    def _extract_headings(self, soup: BeautifulSoup) -> dict[str, list[str]]:
        """Extract h1, h2, h3 headings (max 20 per level)."""
        headings: dict[str, list[str]] = {"h1": [], "h2": [], "h3": []}
        for level in ("h1", "h2", "h3"):
            tags = soup.find_all(level)
            headings[level] = [
                tag.get_text(strip=True) for tag in tags[:20]
            ]
        return headings

    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extract main content text, truncated to MAX_CONTENT_WORDS words.

        Priority: <main> > <article> > largest <div> by text length > <body>.
        """
        element = None

        # Try <main> first
        main_tag = soup.find("main")
        if main_tag:
            element = main_tag

        # Try <article>
        if element is None:
            article_tag = soup.find("article")
            if article_tag:
                element = article_tag

        # Try largest <div> by text length
        if element is None:
            divs = soup.find_all("div")
            if divs:
                element = max(divs, key=lambda d: len(d.get_text(strip=True)))

        # Fall back to body
        if element is None:
            element = soup.find("body")

        if element is None:
            return ""

        text = element.get_text(separator=" ", strip=True)

        # Truncate to MAX_CONTENT_WORDS words
        words = text.split()
        if len(words) > MAX_CONTENT_WORDS:
            words = words[:MAX_CONTENT_WORDS]
        return " ".join(words)

    def _extract_structured_data(self, html: str, url: str) -> dict:
        """Extract JSON-LD, Open Graph, and microdata using extruct.

        Returns dict with keys: json_ld, opengraph, microdata.
        Falls back to empty collections on any error.
        """
        if extruct is None or get_base_url is None:
            logger.warning("extruct or w3lib not installed; skipping structured data extraction")
            return {"json_ld": [], "opengraph": [], "microdata": []}

        try:
            base_url = get_base_url(html, url)
            data = extruct.extract(
                html,
                base_url=base_url,
                syntaxes=["json-ld", "opengraph", "microdata"],
                uniform=True,
            )
            return {
                "json_ld": data.get("json-ld", []),
                "opengraph": data.get("opengraph", []),
                "microdata": data.get("microdata", []),
            }
        except Exception:
            logger.warning("extruct failed to extract structured data", exc_info=True)
            return {"json_ld": [], "opengraph": [], "microdata": []}

    def _extract_open_graph(self, structured: dict) -> dict[str, str]:
        """Flatten Open Graph data from extruct into a simple dict."""
        og_list = structured.get("opengraph", [])
        result: dict[str, str] = {}
        for og_item in og_list:
            if isinstance(og_item, dict):
                for key, value in og_item.items():
                    if isinstance(value, str):
                        result[key] = value
        return result

    def _check_ai_bot_access(self, base_url: str, page_url: str) -> AIBotAccess:
        """Check robots.txt for AI bot directives.

        Fetches robots.txt manually with httpx (sync) and parses with
        RobotFileParser. Returns AIBotAccess with True/False/None per bot.
        """
        robots_url = f"{base_url}/robots.txt"
        try:
            with httpx.Client(timeout=5.0, headers={"User-Agent": USER_AGENT}) as client:
                response = client.get(robots_url)
                if response.status_code != 200:
                    return AIBotAccess()

            rp = RobotFileParser()
            rp.parse(response.text.splitlines())

            access: dict[str, bool | None] = {}
            for user_agent, field_name in AI_BOTS.items():
                # RobotFileParser.can_fetch returns True if no directive exists,
                # so we need to check if the bot is actually mentioned
                can_fetch = rp.can_fetch(user_agent, page_url)
                # Check if this bot is actually mentioned in robots.txt
                bot_mentioned = user_agent.lower() in response.text.lower()
                if bot_mentioned:
                    access[field_name] = can_fetch
                else:
                    access[field_name] = None  # No directive found

            return AIBotAccess(**access)

        except Exception:
            logger.debug("Could not fetch or parse robots.txt at %s", robots_url, exc_info=True)
            return AIBotAccess()

    def _extract_keywords(self, text: str, top_n: int = 20) -> list[str]:
        """Simple keyword extraction using word frequency.

        Lowercases, splits, filters stopwords and short words, returns
        top_n most common words.
        """
        words = re.findall(r"[a-z]+", text.lower())
        filtered = [w for w in words if w not in STOPWORDS and len(w) >= 3]
        counter = Counter(filtered)
        return [word for word, _ in counter.most_common(top_n)]

    def _detect_industry_signals(
        self, schema_org: list[dict], keywords: list[str]
    ) -> list[str]:
        """Detect industry signals from schema.org types and keywords.

        Checks schema.org @type against known industry mappings, then
        checks top keywords against industry keyword lists.
        """
        signals: set[str] = set()

        # Check schema.org types
        for item in schema_org:
            if isinstance(item, dict):
                schema_type = item.get("@type", "")
                if isinstance(schema_type, list):
                    for t in schema_type:
                        if t in SCHEMA_INDUSTRY_MAP:
                            signals.add(SCHEMA_INDUSTRY_MAP[t])
                elif isinstance(schema_type, str) and schema_type in SCHEMA_INDUSTRY_MAP:
                    signals.add(SCHEMA_INDUSTRY_MAP[schema_type])

        # Check keywords against industry keyword lists
        keyword_set = set(keywords)
        for industry, industry_kws in INDUSTRY_KEYWORDS.items():
            matches = keyword_set.intersection(industry_kws)
            if len(matches) >= 2:
                signals.add(industry)

        return sorted(signals)

    def _extract_authority_markers(self, soup: BeautifulSoup) -> dict:
        """Extract E-E-A-T authority markers from the page.

        Checks for: author info, about page link, contact info,
        privacy policy, terms of service.
        """
        # Check for author info
        has_author = False
        meta_author = soup.find("meta", attrs={"name": "author"})
        if meta_author and meta_author.get("content"):
            has_author = True
        # Also check for schema.org Person
        for script in soup.find_all("script", type="application/ld+json"):
            text = script.string or ""
            if '"Person"' in text and '"author"' in text.lower():
                has_author = True
                break

        # Check for about page link
        has_about_link = False
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"].lower()
            if "/about" in href or href.endswith("about"):
                has_about_link = True
                break

        # Check for contact info
        has_contact = False
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"].lower()
            if "/contact" in href or href.startswith("mailto:") or href.startswith("tel:"):
                has_contact = True
                break
        # Also check for phone patterns in text
        if not has_contact:
            body = soup.find("body")
            if body:
                body_text = body.get_text()
                if re.search(r"\+?\d[\d\s\-()]{8,}\d", body_text):
                    has_contact = True

        # Check for privacy policy link
        has_privacy_policy = False
        for a_tag in soup.find_all("a", href=True):
            link_text = a_tag.get_text(strip=True).lower()
            href = a_tag["href"].lower()
            if "privacy" in link_text or "privacy" in href:
                has_privacy_policy = True
                break

        # Check for terms of service link
        has_terms = False
        for a_tag in soup.find_all("a", href=True):
            link_text = a_tag.get_text(strip=True).lower()
            href = a_tag["href"].lower()
            if "terms" in link_text or "terms" in href:
                has_terms = True
                break

        return {
            "has_author": has_author,
            "has_about_link": has_about_link,
            "has_contact": has_contact,
            "has_privacy_policy": has_privacy_policy,
            "has_terms": has_terms,
        }
