"""
SEO-Specific Helper Utilities

Sitemap parsing, robots.txt analysis, canonical validation,
and other SEO-specific operations.
"""

import xml.etree.ElementTree as ET
from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse, urljoin
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import ssl
import socket

from .logging import get_logger
from .http_client import fetch_url, get_base_url


logger = get_logger("seo_helpers")


# ========== Sitemap Parsing ==========

class SitemapAnalyzer:
    """Parse and analyze XML sitemaps."""

    def __init__(self, sitemap_url: str):
        """
        Initialize sitemap analyzer.

        Args:
            sitemap_url: URL to sitemap.xml
        """
        self.sitemap_url = sitemap_url
        self.urls = []
        self.errors = []

    def fetch_and_parse(self) -> bool:
        """
        Fetch and parse sitemap.

        Returns:
            True if successful
        """
        response = fetch_url(self.sitemap_url)

        if not response:
            self.errors.append("Failed to fetch sitemap")
            return False

        try:
            root = ET.fromstring(response.content)

            # Handle namespace
            namespaces = {
                '': 'http://www.sitemaps.org/schemas/sitemap/0.9'
            }

            # Check if this is a sitemap index
            if root.tag.endswith('sitemapindex'):
                return self._parse_sitemap_index(root, namespaces)
            else:
                return self._parse_sitemap(root, namespaces)

        except ET.ParseError as e:
            self.errors.append(f"XML parse error: {str(e)}")
            return False

    def _parse_sitemap(self, root: ET.Element, namespaces: Dict[str, str]) -> bool:
        """Parse regular sitemap."""
        for url_elem in root.findall('.//url', namespaces):
            url_data = {}

            loc = url_elem.find('loc', namespaces)
            if loc is not None and loc.text:
                url_data['loc'] = loc.text.strip()

            lastmod = url_elem.find('lastmod', namespaces)
            if lastmod is not None and lastmod.text:
                url_data['lastmod'] = lastmod.text.strip()

            changefreq = url_elem.find('changefreq', namespaces)
            if changefreq is not None and changefreq.text:
                url_data['changefreq'] = changefreq.text.strip()

            priority = url_elem.find('priority', namespaces)
            if priority is not None and priority.text:
                url_data['priority'] = float(priority.text)

            self.urls.append(url_data)

        return True

    def _parse_sitemap_index(self, root: ET.Element, namespaces: Dict[str, str]) -> bool:
        """Parse sitemap index (contains links to other sitemaps)."""
        for sitemap_elem in root.findall('.//sitemap', namespaces):
            loc = sitemap_elem.find('loc', namespaces)
            if loc is not None and loc.text:
                # Recursively fetch child sitemaps (limit depth to avoid loops)
                child_url = loc.text.strip()
                child_analyzer = SitemapAnalyzer(child_url)
                child_analyzer.fetch_and_parse()
                self.urls.extend(child_analyzer.urls)

        return True

    def get_lastmod_coverage(self) -> Dict[str, Any]:
        """
        Calculate lastmod tag coverage.

        Returns:
            {
                'coverage_percent': float,
                'total_urls': int,
                'urls_with_lastmod': int,
                'urls_without_lastmod': int
            }
        """
        total = len(self.urls)

        if total == 0:
            return {
                'coverage_percent': 0.0,
                'total_urls': 0,
                'urls_with_lastmod': 0,
                'urls_without_lastmod': 0
            }

        with_lastmod = sum(1 for url in self.urls if 'lastmod' in url)
        without_lastmod = total - with_lastmod

        return {
            'coverage_percent': (with_lastmod / total) * 100,
            'total_urls': total,
            'urls_with_lastmod': with_lastmod,
            'urls_without_lastmod': without_lastmod
        }

    def check_lastmod_accuracy(self, sample_size: int = 10) -> Dict[str, Any]:
        """
        Verify lastmod accuracy by checking actual page modification dates.

        Args:
            sample_size: Number of URLs to sample

        Returns:
            Accuracy metrics
        """
        # Sample URLs with lastmod
        urls_with_lastmod = [url for url in self.urls if 'lastmod' in url]

        if not urls_with_lastmod:
            return {'accurate': 0, 'total': 0, 'accuracy_percent': 0.0}

        sample = urls_with_lastmod[:sample_size]
        accurate = 0

        for url_data in sample:
            loc = url_data['loc']
            claimed_lastmod = url_data['lastmod']

            # Fetch URL and check Last-Modified header
            response = fetch_url(loc, use_cache=False)

            if response:
                actual_lastmod = response.headers.get('Last-Modified')

                if actual_lastmod:
                    # Compare dates (allowing some margin)
                    try:
                        claimed_date = datetime.fromisoformat(claimed_lastmod.replace('Z', '+00:00'))
                        actual_date = datetime.strptime(actual_lastmod, '%a, %d %b %Y %H:%M:%S %Z')

                        # Allow 24 hour difference
                        if abs((claimed_date - actual_date).total_seconds()) < 86400:
                            accurate += 1

                    except ValueError:
                        pass

        return {
            'accurate': accurate,
            'total': len(sample),
            'accuracy_percent': (accurate / len(sample)) * 100 if sample else 0.0
        }


# ========== Robots.txt Advanced Analysis ==========

class RobotsTxtAnalyzer:
    """Advanced robots.txt analysis."""

    def __init__(self, url: str):
        """
        Initialize analyzer.

        Args:
            url: Base URL
        """
        self.base_url = get_base_url(url)
        self.robots_url = f"{self.base_url}/robots.txt"
        self.content = None
        self.parser = RobotFileParser()

    def fetch_and_parse(self) -> bool:
        """Fetch and parse robots.txt."""
        try:
            self.parser.set_url(self.robots_url)
            self.parser.read()

            # Also fetch raw content for analysis
            response = fetch_url(self.robots_url)
            if response:
                self.content = response.text

            return True

        except Exception as e:
            logger.warning(f"Failed to parse robots.txt: {str(e)}")
            return False

    def check_user_agent(self, user_agent: str, path: str = '/') -> bool:
        """
        Check if user agent can access path.

        Args:
            user_agent: User agent string
            path: Path to check

        Returns:
            True if allowed
        """
        return self.parser.can_fetch(user_agent, urljoin(self.base_url, path))

    def check_resource_blockage(self) -> Dict[str, bool]:
        """
        Check if critical resources (CSS, JS) are blocked.

        Returns:
            {
                'css_blocked': bool,
                'js_blocked': bool,
                'images_blocked': bool
            }
        """
        test_paths = {
            'css': '/static/style.css',
            'js': '/static/script.js',
            'images': '/images/logo.png'
        }

        # Test with Googlebot
        return {
            f'{resource}_blocked': not self.check_user_agent('Googlebot', path)
            for resource, path in test_paths.items()
        }

    def get_crawl_delay(self, user_agent: str = 'Googlebot') -> Optional[float]:
        """
        Get crawl-delay directive for user agent.

        Returns:
            Delay in seconds or None
        """
        if not self.content:
            return None

        # Parse crawl-delay manually (not in urllib.robotparser)
        lines = self.content.lower().split('\n')
        current_agent = None

        for line in lines:
            line = line.strip()

            if line.startswith('user-agent:'):
                current_agent = line.split(':', 1)[1].strip()

            if current_agent == user_agent.lower() and line.startswith('crawl-delay:'):
                try:
                    delay = float(line.split(':', 1)[1].strip())
                    return delay
                except ValueError:
                    pass

        return None

    def get_sitemap_urls(self) -> List[str]:
        """Extract sitemap URLs from robots.txt."""
        if not self.content:
            return []

        sitemaps = []
        for line in self.content.split('\n'):
            line = line.strip()
            if line.lower().startswith('sitemap:'):
                sitemap_url = line.split(':', 1)[1].strip()
                sitemaps.append(sitemap_url)

        return sitemaps


# ========== SSL Certificate Check ==========

def check_ssl_certificate(domain: str) -> Dict[str, Any]:
    """
    Check SSL certificate validity.

    Args:
        domain: Domain name (without protocol)

    Returns:
        {
            'valid': bool,
            'issuer': str,
            'expires': datetime,
            'days_until_expiry': int,
            'protocol': str
        }
    """
    parsed = urlparse(domain)
    hostname = parsed.netloc if parsed.netloc else domain

    # Remove port if present
    hostname = hostname.split(':')[0]

    try:
        context = ssl.create_default_context()
        with socket.create_connection((hostname, 443), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()

                # Extract expiry
                not_after = cert['notAfter']
                expiry_date = datetime.strptime(not_after, '%b %d %H:%M:%S %Y %Z')
                days_until_expiry = (expiry_date - datetime.now()).days

                # Extract issuer
                issuer = dict(x[0] for x in cert['issuer'])

                return {
                    'valid': True,
                    'issuer': issuer.get('organizationName', 'Unknown'),
                    'expires': expiry_date,
                    'days_until_expiry': days_until_expiry,
                    'protocol': ssock.version(),
                    'subject': dict(x[0] for x in cert['subject'])
                }

    except Exception as e:
        logger.warning(f"SSL check failed for {hostname}: {str(e)}")
        return {
            'valid': False,
            'error': str(e)
        }


# ========== Canonical Tag Validation ==========

def validate_canonical(html: str, current_url: str) -> Dict[str, Any]:
    """
    Validate canonical tag implementation.

    Args:
        html: HTML content
        current_url: Current page URL

    Returns:
        {
            'has_canonical': bool,
            'canonical_url': str,
            'is_self_canonical': bool,
            'issues': List[str]
        }
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, 'lxml')
    canonical_tag = soup.find('link', rel='canonical')

    issues = []

    if not canonical_tag:
        return {
            'has_canonical': False,
            'canonical_url': '',
            'is_self_canonical': False,
            'issues': ['No canonical tag found']
        }

    canonical_url = canonical_tag.get('href', '').strip()

    if not canonical_url:
        issues.append('Canonical tag present but empty')

    # Check if self-canonical
    current_url_normalized = current_url.rstrip('/')
    canonical_url_normalized = canonical_url.rstrip('/')

    is_self_canonical = current_url_normalized == canonical_url_normalized

    # Check for multiple canonical tags
    all_canonicals = soup.find_all('link', rel='canonical')
    if len(all_canonicals) > 1:
        issues.append(f'Multiple canonical tags found ({len(all_canonicals)})')

    return {
        'has_canonical': True,
        'canonical_url': canonical_url,
        'is_self_canonical': is_self_canonical,
        'issues': issues,
        'multiple_tags': len(all_canonicals) > 1
    }


# ========== Hreflang Validation ==========

def validate_hreflang(html: str) -> Dict[str, Any]:
    """
    Validate hreflang implementation.

    Returns:
        {
            'has_hreflang': bool,
            'count': int,
            'languages': List[str],
            'issues': List[str]
        }
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, 'lxml')
    hreflang_tags = soup.find_all('link', rel='alternate', hreflang=True)

    issues = []
    languages = []

    for tag in hreflang_tags:
        lang = tag.get('hreflang', '')
        href = tag.get('href', '')

        languages.append(lang)

        if not href:
            issues.append(f'Hreflang tag for {lang} has no href')

        # Check for x-default
        if lang == 'x-default' and not href:
            issues.append('x-default hreflang has no href')

    # Check for x-default presence (best practice)
    if hreflang_tags and 'x-default' not in languages:
        issues.append('Missing x-default hreflang (recommended)')

    return {
        'has_hreflang': len(hreflang_tags) > 0,
        'count': len(hreflang_tags),
        'languages': list(set(languages)),
        'issues': issues
    }


# ========== URL Analysis ==========

def analyze_url_structure(url: str) -> Dict[str, Any]:
    """
    Analyze URL structure for SEO best practices.

    Returns:
        {
            'length': int,
            'has_https': bool,
            'has_www': bool,
            'path_depth': int,
            'has_parameters': bool,
            'has_fragment': bool,
            'is_clean': bool,
            'issues': List[str]
        }
    """
    parsed = urlparse(url)
    issues = []

    # Check HTTPS
    has_https = parsed.scheme == 'https'
    if not has_https:
        issues.append('Not using HTTPS')

    # Check WWW
    has_www = parsed.netloc.startswith('www.')

    # Path depth
    path_segments = [s for s in parsed.path.split('/') if s]
    path_depth = len(path_segments)

    if path_depth > 3:
        issues.append(f'Deep path ({path_depth} levels)')

    # Check for parameters
    has_parameters = bool(parsed.query)
    if has_parameters:
        issues.append('Contains query parameters')

    # Check for fragment
    has_fragment = bool(parsed.fragment)

    # Check URL length
    url_length = len(url)
    if url_length > 100:
        issues.append(f'Long URL ({url_length} characters)')

    # Check for clean structure (no special chars, underscores)
    is_clean = not re.search(r'[_~#\[\]@!$&()*+,;=]', parsed.path)
    if not is_clean:
        issues.append('URL contains special characters')

    return {
        'length': url_length,
        'has_https': has_https,
        'has_www': has_www,
        'path_depth': path_depth,
        'has_parameters': has_parameters,
        'has_fragment': has_fragment,
        'is_clean': is_clean,
        'issues': issues
    }
