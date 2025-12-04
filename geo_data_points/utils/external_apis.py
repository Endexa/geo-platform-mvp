"""
External API Clients

Clients for Google Knowledge Graph, Wikidata, Wikipedia, PageSpeed Insights,
social media APIs, and SEO tools with rate limiting and error handling.
"""

import requests
from typing import Optional, Dict, Any, List
from functools import lru_cache
import time
from threading import Lock

from .logging import get_logger
from .config import get_config
from .http_client import get_http_session


logger = get_logger("external_apis")
config = get_config()


class RateLimiter:
    """Simple rate limiter for API calls."""

    def __init__(self, calls_per_minute: int = 60):
        self.calls_per_minute = calls_per_minute
        self.calls = []
        self.lock = Lock()

    def wait_if_needed(self):
        """Wait if rate limit would be exceeded."""
        with self.lock:
            now = time.time()

            # Remove calls older than 1 minute
            self.calls = [call_time for call_time in self.calls if now - call_time < 60]

            # Check if we need to wait
            if len(self.calls) >= self.calls_per_minute:
                oldest_call = min(self.calls)
                sleep_time = 60 - (now - oldest_call)

                if sleep_time > 0:
                    logger.debug(f"Rate limit reached, sleeping for {sleep_time:.2f}s")
                    time.sleep(sleep_time)

            # Record this call
            self.calls.append(time.time())


# ========== Google Knowledge Graph ==========

class GoogleKnowledgeGraphClient:
    """Client for Google Knowledge Graph Search API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or config.GOOGLE_PAGESPEED_API_KEY
        self.base_url = "https://kgsearch.googleapis.com/v1/entities:search"
        self.rate_limiter = RateLimiter(calls_per_minute=100)

    @lru_cache(maxsize=1000)
    def search_entity(self, query: str, limit: int = 1) -> Optional[Dict[str, Any]]:
        """
        Search Knowledge Graph for entity.

        Args:
            query: Search query (brand name, person, etc.)
            limit: Number of results

        Returns:
            API response or None
        """
        if not self.api_key:
            logger.warning("Google KG API key not configured")
            return None

        self.rate_limiter.wait_if_needed()

        params = {
            'query': query,
            'limit': limit,
            'indent': True,
            'key': self.api_key
        }

        try:
            session = get_http_session()
            response = session.get(self.base_url, params=params, use_cache=True)

            if response and response.status_code == 200:
                return response.json()

            logger.warning(f"KG API error: {response.status_code if response else 'No response'}")
            return None

        except Exception as e:
            logger.error(f"KG API exception: {str(e)}")
            return None

    def get_entity_info(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Get entity information including kg_mid and confidence.

        Returns:
            {
                'kg_mid': str,
                'name': str,
                'description': str,
                'confidence_score': float,
                'types': List[str],
                'url': str
            }
        """
        result = self.search_entity(query)

        if not result or 'itemListElement' not in result:
            return None

        if not result['itemListElement']:
            return None

        # Get first result
        entity = result['itemListElement'][0].get('result', {})

        return {
            'kg_mid': entity.get('@id', '').replace('kg:', ''),
            'name': entity.get('name', ''),
            'description': entity.get('description', ''),
            'confidence_score': result['itemListElement'][0].get('resultScore', 0.0),
            'types': entity.get('@type', []),
            'url': entity.get('url', '')
        }


# ========== Wikidata ==========

class WikidataClient:
    """Client for Wikidata API."""

    def __init__(self):
        self.base_url = "https://www.wikidata.org/w/api.php"
        self.rate_limiter = RateLimiter(calls_per_minute=200)

    @lru_cache(maxsize=1000)
    def search_entity(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """
        Search for Wikidata entity.

        Args:
            query: Search query

        Returns:
            List of matching entities
        """
        self.rate_limiter.wait_if_needed()

        params = {
            'action': 'wbsearchentities',
            'search': query,
            'language': 'en',
            'format': 'json'
        }

        try:
            session = get_http_session()
            response = session.get(self.base_url, params=params, use_cache=True)

            if response and response.status_code == 200:
                data = response.json()
                return data.get('search', [])

            return None

        except Exception as e:
            logger.error(f"Wikidata API exception: {str(e)}")
            return None

    def get_entity_by_id(self, qid: str) -> Optional[Dict[str, Any]]:
        """
        Get entity details by QID.

        Args:
            qid: Wikidata QID (e.g., Q312)

        Returns:
            Entity data
        """
        self.rate_limiter.wait_if_needed()

        params = {
            'action': 'wbgetentities',
            'ids': qid,
            'format': 'json'
        }

        try:
            session = get_http_session()
            response = session.get(self.base_url, params=params, use_cache=True)

            if response and response.status_code == 200:
                data = response.json()
                return data.get('entities', {}).get(qid)

            return None

        except Exception as e:
            logger.error(f"Wikidata API exception: {str(e)}")
            return None

    def find_entity_qid(self, query: str) -> Optional[str]:
        """
        Find QID for a query.

        Args:
            query: Search query

        Returns:
            QID or None
        """
        results = self.search_entity(query)

        if results and len(results) > 0:
            return results[0].get('id')

        return None


# ========== Wikipedia ==========

class WikipediaClient:
    """Client for Wikipedia API."""

    def __init__(self):
        self.base_url = "https://en.wikipedia.org/w/api.php"
        self.rate_limiter = RateLimiter(calls_per_minute=200)

    @lru_cache(maxsize=1000)
    def search_page(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """
        Search Wikipedia pages.

        Args:
            query: Search query

        Returns:
            List of matching pages
        """
        self.rate_limiter.wait_if_needed()

        params = {
            'action': 'opensearch',
            'search': query,
            'limit': 10,
            'format': 'json'
        }

        try:
            session = get_http_session()
            response = session.get(self.base_url, params=params, use_cache=True)

            if response and response.status_code == 200:
                data = response.json()

                # opensearch returns [query, titles, descriptions, urls]
                if len(data) >= 4:
                    titles = data[1]
                    descriptions = data[2]
                    urls = data[3]

                    return [
                        {'title': t, 'description': d, 'url': u}
                        for t, d, u in zip(titles, descriptions, urls)
                    ]

            return None

        except Exception as e:
            logger.error(f"Wikipedia API exception: {str(e)}")
            return None

    def check_page_exists(self, title: str) -> bool:
        """
        Check if Wikipedia page exists.

        Args:
            title: Page title

        Returns:
            True if page exists
        """
        results = self.search_page(title)
        return results is not None and len(results) > 0

    @lru_cache(maxsize=1000)
    def get_backlinks_count(self, domain: str) -> int:
        """
        Get count of Wikipedia pages linking to domain.

        Args:
            domain: Domain name (e.g., "anthropic.com")

        Returns:
            Number of backlinks
        """
        self.rate_limiter.wait_if_needed()

        params = {
            'action': 'query',
            'list': 'exturlusage',
            'euquery': domain,
            'eulimit': 500,
            'format': 'json'
        }

        try:
            session = get_http_session()
            response = session.get(self.base_url, params=params, use_cache=True)

            if response and response.status_code == 200:
                data = response.json()
                results = data.get('query', {}).get('exturlusage', [])
                return len(results)

            return 0

        except Exception as e:
            logger.error(f"Wikipedia backlinks API exception: {str(e)}")
            return 0


# ========== PageSpeed Insights ==========

class PageSpeedClient:
    """Client for Google PageSpeed Insights API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or config.GOOGLE_PAGESPEED_API_KEY
        self.base_url = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
        self.rate_limiter = RateLimiter(calls_per_minute=25)

    @lru_cache(maxsize=100)
    def analyze_url(self, url: str, strategy: str = 'mobile') -> Optional[Dict[str, Any]]:
        """
        Analyze URL with PageSpeed Insights.

        Args:
            url: Target URL
            strategy: 'mobile' or 'desktop'

        Returns:
            PageSpeed results
        """
        if not self.api_key:
            logger.warning("PageSpeed API key not configured")
            return None

        self.rate_limiter.wait_if_needed()

        params = {
            'url': url,
            'strategy': strategy,
            'key': self.api_key
        }

        try:
            session = get_http_session()
            response = session.get(self.base_url, params=params, use_cache=True, timeout=30)

            if response and response.status_code == 200:
                return response.json()

            logger.warning(f"PageSpeed API error: {response.status_code if response else 'No response'}")
            return None

        except Exception as e:
            logger.error(f"PageSpeed API exception: {str(e)}")
            return None

    def get_core_web_vitals(self, url: str, strategy: str = 'mobile') -> Optional[Dict[str, float]]:
        """
        Extract Core Web Vitals metrics.

        Returns:
            {
                'lcp': float (ms),
                'fid': float (ms),
                'cls': float,
                'performance_score': int (0-100)
            }
        """
        result = self.analyze_url(url, strategy)

        if not result:
            return None

        lighthouse = result.get('lighthouseResult', {})
        audits = lighthouse.get('audits', {})

        # Extract metrics
        lcp_data = audits.get('largest-contentful-paint', {})
        fid_data = audits.get('max-potential-fid', {})  # FID proxy
        cls_data = audits.get('cumulative-layout-shift', {})

        performance_score = lighthouse.get('categories', {}).get('performance', {}).get('score', 0) * 100

        return {
            'lcp': lcp_data.get('numericValue', 0),
            'fid': fid_data.get('numericValue', 0),
            'cls': cls_data.get('numericValue', 0),
            'performance_score': int(performance_score)
        }


# ========== Reddit API ==========

class RedditClient:
    """Client for Reddit API (read-only)."""

    def __init__(self):
        self.base_url = "https://www.reddit.com"
        self.rate_limiter = RateLimiter(calls_per_minute=60)

    @lru_cache(maxsize=100)
    def search_mentions(self, query: str, limit: int = 100) -> int:
        """
        Count brand mentions on Reddit.

        Args:
            query: Brand name to search
            limit: Max results

        Returns:
            Number of mentions
        """
        self.rate_limiter.wait_if_needed()

        url = f"{self.base_url}/search.json"
        params = {
            'q': query,
            'limit': limit,
            'sort': 'relevance'
        }

        headers = {
            'User-Agent': 'GEO-Platform-Bot/1.0'
        }

        try:
            session = get_http_session()
            response = session.get(url, params=params, headers=headers, use_cache=True)

            if response and response.status_code == 200:
                data = response.json()
                posts = data.get('data', {}).get('children', [])
                return len(posts)

            return 0

        except Exception as e:
            logger.error(f"Reddit API exception: {str(e)}")
            return 0


# ========== Common Crawl ==========

class CommonCrawlClient:
    """Client for Common Crawl Index API."""

    def __init__(self):
        self.base_url = "https://index.commoncrawl.org/CC-MAIN-2024-10-index"
        self.rate_limiter = RateLimiter(calls_per_minute=30)

    @lru_cache(maxsize=100)
    def get_domain_page_count(self, domain: str) -> int:
        """
        Get count of pages from domain in Common Crawl.

        Args:
            domain: Domain name

        Returns:
            Number of pages indexed
        """
        self.rate_limiter.wait_if_needed()

        url = f"{self.base_url}?url={domain}/*&output=json"

        try:
            session = get_http_session()
            response = session.get(url, use_cache=True, timeout=10)

            if response and response.status_code == 200:
                # Count newline-delimited JSON records
                lines = response.text.strip().split('\n')
                return len(lines)

            return 0

        except Exception as e:
            logger.error(f"Common Crawl API exception: {str(e)}")
            return 0


# ========== Global Client Instances ==========

_kg_client = None
_wikidata_client = None
_wikipedia_client = None
_pagespeed_client = None
_reddit_client = None
_commoncrawl_client = None


def get_knowledge_graph_client() -> GoogleKnowledgeGraphClient:
    """Get global KG client instance."""
    global _kg_client
    if _kg_client is None:
        _kg_client = GoogleKnowledgeGraphClient()
    return _kg_client


def get_wikidata_client() -> WikidataClient:
    """Get global Wikidata client instance."""
    global _wikidata_client
    if _wikidata_client is None:
        _wikidata_client = WikidataClient()
    return _wikidata_client


def get_wikipedia_client() -> WikipediaClient:
    """Get global Wikipedia client instance."""
    global _wikipedia_client
    if _wikipedia_client is None:
        _wikipedia_client = WikipediaClient()
    return _wikipedia_client


def get_pagespeed_client() -> PageSpeedClient:
    """Get global PageSpeed client instance."""
    global _pagespeed_client
    if _pagespeed_client is None:
        _pagespeed_client = PageSpeedClient()
    return _pagespeed_client


def get_reddit_client() -> RedditClient:
    """Get global Reddit client instance."""
    global _reddit_client
    if _reddit_client is None:
        _reddit_client = RedditClient()
    return _reddit_client


def get_commoncrawl_client() -> CommonCrawlClient:
    """Get global Common Crawl client instance."""
    global _commoncrawl_client
    if _commoncrawl_client is None:
        _commoncrawl_client = CommonCrawlClient()
    return _commoncrawl_client
