"""
HTTP Client Utilities

High-performance HTTP client with connection pooling, retries, caching,
and support for billions of daily requests.
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Optional, Dict, Any, List
from functools import lru_cache
import hashlib
from datetime import datetime, timedelta
from threading import Lock

from .logging import get_logger
from .config import get_config


logger = get_logger("http_client")
config = get_config()


class CachedSession:
    """Thread-safe HTTP session with caching and connection pooling."""

    _instance = None
    _lock = Lock()
    _cache: Dict[str, tuple] = {}
    _cache_ttl = 300  # 5 minutes default

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.session = requests.Session()

        # Connection pooling for high throughput
        adapter = HTTPAdapter(
            pool_connections=100,
            pool_maxsize=100,
            max_retries=Retry(
                total=config.MAX_RETRIES,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["GET", "POST", "HEAD"]
            )
        )

        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Default headers
        self.session.headers.update({
            'User-Agent': config.USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
        })

        self._initialized = True

    def _cache_key(self, url: str, method: str, params: Optional[Dict] = None) -> str:
        """Generate cache key from request parameters."""
        key_parts = [method, url]
        if params:
            key_parts.append(str(sorted(params.items())))
        return hashlib.md5(''.join(key_parts).encode()).hexdigest()

    def _get_from_cache(self, cache_key: str) -> Optional[requests.Response]:
        """Retrieve response from cache if valid."""
        if cache_key in self._cache:
            response, timestamp = self._cache[cache_key]
            if datetime.now() - timestamp < timedelta(seconds=self._cache_ttl):
                logger.debug(f"Cache hit: {cache_key}")
                return response
            else:
                del self._cache[cache_key]
        return None

    def _save_to_cache(self, cache_key: str, response: requests.Response):
        """Save response to cache."""
        # Limit cache size
        if len(self._cache) > 10000:
            # Remove oldest 10%
            sorted_items = sorted(self._cache.items(), key=lambda x: x[1][1])
            for key, _ in sorted_items[:1000]:
                del self._cache[key]

        self._cache[cache_key] = (response, datetime.now())

    def get(self, url: str, use_cache: bool = True, timeout: Optional[int] = None,
            **kwargs) -> Optional[requests.Response]:
        """
        GET request with caching and error handling.

        Args:
            url: Target URL
            use_cache: Whether to use cache
            timeout: Request timeout (default from config)
            **kwargs: Additional requests parameters

        Returns:
            Response object or None on failure
        """
        timeout = timeout or config.REQUEST_TIMEOUT

        # Check cache
        if use_cache:
            cache_key = self._cache_key(url, 'GET', kwargs.get('params'))
            cached_response = self._get_from_cache(cache_key)
            if cached_response:
                return cached_response

        try:
            response = self.session.get(url, timeout=timeout, **kwargs)
            response.raise_for_status()

            # Save to cache
            if use_cache and response.status_code == 200:
                self._save_to_cache(cache_key, response)

            return response

        except requests.exceptions.Timeout:
            logger.warning(f"Timeout fetching {url}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Error fetching {url}: {str(e)}")

        return None

    def head(self, url: str, timeout: Optional[int] = None, **kwargs) -> Optional[requests.Response]:
        """HEAD request for checking URL status without fetching body."""
        timeout = timeout or config.REQUEST_TIMEOUT

        try:
            response = self.session.head(url, timeout=timeout, allow_redirects=True, **kwargs)
            return response
        except requests.exceptions.RequestException as e:
            logger.warning(f"HEAD request failed for {url}: {str(e)}")
            return None

    def post(self, url: str, timeout: Optional[int] = None, **kwargs) -> Optional[requests.Response]:
        """POST request."""
        timeout = timeout or config.REQUEST_TIMEOUT

        try:
            response = self.session.post(url, timeout=timeout, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.warning(f"POST request failed for {url}: {str(e)}")
            return None

    def clear_cache(self):
        """Clear HTTP cache."""
        self._cache.clear()
        logger.info("HTTP cache cleared")


# Global session instance
_http_session = CachedSession()


def get_http_session() -> CachedSession:
    """Get global HTTP session instance."""
    return _http_session


def fetch_url(url: str, use_cache: bool = True, timeout: Optional[int] = None,
              headers: Optional[Dict[str, str]] = None) -> Optional[requests.Response]:
    """
    Fetch URL with caching and retries.

    Args:
        url: Target URL
        use_cache: Whether to use cache
        timeout: Request timeout
        headers: Additional headers

    Returns:
        Response object or None
    """
    session = get_http_session()
    kwargs = {}
    if headers:
        kwargs['headers'] = headers

    return session.get(url, use_cache=use_cache, timeout=timeout, **kwargs)


def check_url_status(url: str) -> tuple[bool, int, str]:
    """
    Check URL status with HEAD request.

    Returns:
        (is_accessible, status_code, final_url)
    """
    session = get_http_session()
    response = session.head(url)

    if response:
        return (response.status_code == 200, response.status_code, response.url)

    return (False, 0, url)


def follow_redirects(url: str, max_hops: int = 10) -> List[Dict[str, Any]]:
    """
    Follow redirect chain and return all hops.

    Returns:
        List of dicts with 'url', 'status_code', 'location'
    """
    session = get_http_session()
    redirects = []
    current_url = url

    for hop in range(max_hops):
        try:
            response = session.session.get(
                current_url,
                timeout=config.REQUEST_TIMEOUT,
                allow_redirects=False
            )

            redirects.append({
                'url': current_url,
                'status_code': response.status_code,
                'location': response.headers.get('Location', '')
            })

            # Check if redirect
            if response.status_code in [301, 302, 303, 307, 308]:
                location = response.headers.get('Location')
                if not location:
                    break

                # Handle relative URLs
                if location.startswith('/'):
                    from urllib.parse import urlparse, urljoin
                    current_url = urljoin(current_url, location)
                else:
                    current_url = location
            else:
                break

        except requests.exceptions.RequestException as e:
            logger.warning(f"Error following redirects: {str(e)}")
            break

    return redirects


def measure_response_time(url: str) -> tuple[float, int]:
    """
    Measure time to first byte (TTFB).

    Returns:
        (ttfb_ms, status_code)
    """
    import time

    session = get_http_session()
    start_time = time.time()

    try:
        response = session.session.get(
            url,
            timeout=config.REQUEST_TIMEOUT,
            stream=True  # Don't download full body
        )

        # Read first byte
        next(response.iter_content(1), None)

        ttfb = (time.time() - start_time) * 1000
        return (ttfb, response.status_code)

    except requests.exceptions.RequestException:
        return (0.0, 0)


def get_final_url(url: str) -> str:
    """
    Get final URL after following all redirects.

    Args:
        url: Initial URL

    Returns:
        Final URL
    """
    session = get_http_session()
    response = session.head(url)

    if response:
        return response.url

    return url


def check_robots_txt_allows(url: str, user_agent: str, use_cache: bool = True) -> Optional[bool]:
    """
    Check if user agent is allowed by robots.txt.

    Args:
        url: Target URL
        user_agent: User agent string
        use_cache: Whether to cache robots.txt

    Returns:
        True if allowed, False if blocked, None if no robots.txt
    """
    from urllib.robotparser import RobotFileParser
    from urllib.parse import urlparse

    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    # Check cache
    cache_key = f"robots_{robots_url}_{user_agent}"
    if use_cache and hasattr(check_robots_txt_allows, '_cache'):
        if cache_key in check_robots_txt_allows._cache:
            return check_robots_txt_allows._cache[cache_key]

    try:
        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.read()

        result = rp.can_fetch(user_agent, url)

        # Cache result
        if use_cache:
            if not hasattr(check_robots_txt_allows, '_cache'):
                check_robots_txt_allows._cache = {}
            check_robots_txt_allows._cache[cache_key] = result

        return result

    except Exception:
        return None


def get_base_url(url: str) -> str:
    """
    Extract base URL from a given URL.

    Args:
        url: Full URL

    Returns:
        Base URL (scheme://netloc)
    """
    from urllib.parse import urlparse

    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"
