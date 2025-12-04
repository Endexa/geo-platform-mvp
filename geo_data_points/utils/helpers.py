"""
GEO Data Points Helper Utilities

Common functions for URL validation, HTTP requests, HTML parsing, etc.
"""

import requests
import time
from typing import Optional, Dict, Any
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import re

from .config import get_config
from .logging import get_logger


logger = get_logger("geo_helpers")
config = get_config()


def validate_url(url: str) -> bool:
    """
    Validate URL format.

    Args:
        url: URL to validate

    Returns:
        True if valid, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme in ('http', 'https'), result.netloc])
    except Exception:
        return False


def normalize_url(url: str) -> str:
    """
    Normalize URL (add https:// if missing, remove trailing slash).

    Args:
        url: URL to normalize

    Returns:
        Normalized URL
    """
    url = url.strip()

    # Add https:// if no scheme
    if not url.startswith(('http://', 'https://')):
        url = f"https://{url}"

    # Remove trailing slash
    if url.endswith('/'):
        url = url[:-1]

    return url


def fetch_url(url: str, timeout: Optional[int] = None, retries: Optional[int] = None) -> Optional[requests.Response]:
    """
    Fetch URL with retries and timeout.

    Args:
        url: URL to fetch
        timeout: Request timeout in seconds (defaults to config)
        retries: Number of retries (defaults to config)

    Returns:
        requests.Response object or None on failure
    """
    timeout = timeout or config.REQUEST_TIMEOUT
    retries = retries or config.MAX_RETRIES

    headers = {
        'User-Agent': config.USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
            response.raise_for_status()
            return response
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout fetching {url} (attempt {attempt + 1}/{retries})")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Error fetching {url} (attempt {attempt + 1}/{retries}): {str(e)}")

        if attempt < retries - 1:
            time.sleep(1 * (attempt + 1))  # Exponential backoff

    logger.error(f"Failed to fetch {url} after {retries} attempts")
    return None


def parse_html(html: str) -> Optional[BeautifulSoup]:
    """
    Parse HTML content with BeautifulSoup.

    Args:
        html: HTML content string

    Returns:
        BeautifulSoup object or None on failure
    """
    try:
        return BeautifulSoup(html, 'html.parser')
    except Exception as e:
        logger.error(f"Failed to parse HTML: {str(e)}")
        return None


def extract_text(soup: BeautifulSoup, remove_scripts: bool = True) -> str:
    """
    Extract clean text from BeautifulSoup object.

    Args:
        soup: BeautifulSoup object
        remove_scripts: Remove script and style tags

    Returns:
        Extracted text
    """
    if remove_scripts:
        for script in soup(['script', 'style', 'noscript']):
            script.decompose()

    text = soup.get_text(separator=' ', strip=True)

    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


def get_domain(url: str) -> str:
    """
    Extract domain from URL.

    Args:
        url: Full URL

    Returns:
        Domain (e.g., 'example.com')
    """
    parsed = urlparse(url)
    return parsed.netloc


def get_base_url(url: str) -> str:
    """
    Get base URL (scheme + domain).

    Args:
        url: Full URL

    Returns:
        Base URL (e.g., 'https://example.com')
    """
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def make_absolute_url(base_url: str, relative_url: str) -> str:
    """
    Convert relative URL to absolute URL.

    Args:
        base_url: Base URL
        relative_url: Relative URL

    Returns:
        Absolute URL
    """
    return urljoin(base_url, relative_url)


def calculate_percentage_score(value: float, min_value: float, max_value: float, invert: bool = False) -> float:
    """
    Calculate percentage score (0-100) from value within range.

    Args:
        value: Current value
        min_value: Minimum value (0%)
        max_value: Maximum value (100%)
        invert: If True, higher value = lower score

    Returns:
        Score from 0 to 100
    """
    if max_value == min_value:
        return 50.0

    # Clamp value to range
    value = max(min_value, min(max_value, value))

    # Calculate percentage
    percentage = ((value - min_value) / (max_value - min_value)) * 100

    # Invert if needed (e.g., lower response time = higher score)
    if invert:
        percentage = 100 - percentage

    return round(percentage, 2)


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Safe division with default value on division by zero.

    Args:
        numerator: Numerator
        denominator: Denominator
        default: Default value if denominator is 0

    Returns:
        Division result or default
    """
    if denominator == 0:
        return default
    return numerator / denominator


def format_duration(milliseconds: float) -> str:
    """
    Format duration in milliseconds to human-readable string.

    Args:
        milliseconds: Duration in ms

    Returns:
        Formatted string (e.g., '1.5s', '250ms')
    """
    if milliseconds >= 1000:
        return f"{milliseconds / 1000:.1f}s"
    return f"{int(milliseconds)}ms"
