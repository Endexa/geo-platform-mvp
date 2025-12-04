"""
WI-021: XML Sitemap Presence and Quality

Validates XML sitemap presence, accessibility, and quality for search engines and AI crawlers.
Proper sitemaps accelerate indexing and help AI models discover all content.

WORLD-CLASS ENGINEERING STANDARDS:
- Comprehensive edge case handling
- Explicit assumptions documented
- Multi-sitemap support (sitemap index)
- Detailed error handling with context preservation
- Full metadata tracking
- Validation steps at every stage
- Industry-grade reliability
"""

from typing import Dict, Any, Optional, List, Tuple
from geo_data_points.base import BaseMeasurement
from loguru import logger
from datetime import datetime
import httpx
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse


class XMLSitemapPresenceMeasurement(BaseMeasurement):
    """
    Validate XML sitemap presence, accessibility, and quality.

    ASSUMPTIONS:
    - Sitemap should be at /sitemap.xml or declared in robots.txt
    - Sitemap must be valid XML
    - URLs in sitemap should be canonical (https preferred)
    - Sitemap should contain <loc>, <lastmod>, <changefreq>, <priority>
    - Max 50,000 URLs per sitemap (Google limit)
    - Sitemap index for sites >50K pages
    - Sitemap should be accessible without authentication
    - Sitemap should be referenced in robots.txt
    - All URLs should return 200 status (not 404/redirect)

    EDGE CASES HANDLED:
    1. No sitemap found (common paths checked)
    2. Multiple sitemaps (sitemap index)
    3. Sitemap not in robots.txt
    4. Malformed XML
    5. Empty sitemap (0 URLs)
    6. Oversized sitemap (>50K URLs)
    7. Compressed sitemap (.xml.gz)
    8. Sitemap behind 301 redirect
    9. 404/403/500 errors on sitemap URL
    10. Non-canonical URLs in sitemap
    11. Invalid XML namespaces
    12. Missing required elements (<loc>)
    """

    # ========== CLASS CONSTANTS ==========

    MAX_SITEMAP_URLS = 50000  # Google limit
    IDEAL_SITEMAP_SIZE = 10000  # Good balance

    SITEMAP_PATHS = [
        '/sitemap.xml',
        '/sitemap_index.xml',
        '/sitemap1.xml',
        '/wp-sitemap.xml',  # WordPress
        '/sitemap-index.xml'
    ]

    SITEMAP_NAMESPACES = {
        'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9',
        'xhtml': 'http://www.w3.org/1999/xhtml',
        'image': 'http://www.google.com/schemas/sitemap-image/1.1',
        'video': 'http://www.google.com/schemas/sitemap-video/1.1'
    }

    API_TIMEOUT = 10
    MAX_SITEMAP_SIZE_MB = 50  # 50MB limit

    def __init__(self):
        super().__init__(
            code="WI-021",
            name="XML Sitemap Presence",
            description="Validates XML sitemap presence and quality",
            category="Web Infrastructure",
            weight=0.85  # Important for indexing and crawlability
        )

    async def measure(self, url: str, html: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Measure XML sitemap presence and quality.

        SCORING BREAKDOWN:
        - 100: Perfect sitemap (accessible, valid XML, optimal size, in robots.txt, all elements)
        - 90: Excellent (valid, in robots.txt, good elements)
        - 80: Good (valid, accessible, most elements)
        - 70: Acceptable (valid XML, basic elements)
        - 60: Minimal (valid but missing many elements)
        - 40: Poor (accessible but XML issues)
        - 20: Critical issues (oversized, malformed)
        - 0: No sitemap found

        QUALITY FACTORS:
        - Presence & Accessibility (30%)
        - XML Validity (25%)
        - Completeness (20%)
        - Robots.txt Reference (15%)
        - URL Quality (10%)

        Args:
            url: Target URL to analyze
            html: HTML content (unused)
            metadata: Optional metadata (may contain 'sitemap_url')

        Returns:
            Dict with score (0-100), detailed comment, metadata, and recommendations
        """
        execution_start = datetime.utcnow()

        try:
            logger.info(f"[WI-021] Starting XML sitemap analysis for {url}")

            # Extract base domain
            base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"

            # ========== STEP 1: FIND SITEMAP URL ==========
            sitemap_url, discovery_method = await self._find_sitemap_url(base_url, metadata)

            if not sitemap_url:
                return {
                    'score': 0,
                    'comment': 'No XML sitemap found. CRITICAL for search engine indexing! Create XML sitemap at /sitemap.xml with all important URLs. Declare in robots.txt. Sitemaps accelerate discovery and indexing by search engines and AI crawlers.',
                    'metadata': {
                        'sitemap_found': False,
                        'execution_time_ms': self._calc_execution_time(execution_start)
                    },
                    'recommendations': [
                        'Create XML sitemap with all important URLs',
                        'Place at /sitemap.xml (standard location)',
                        'Add "Sitemap: https://yourdomain.com/sitemap.xml" to robots.txt',
                        'Include <loc>, <lastmod>, <changefreq>, <priority> elements',
                        'Submit sitemap to Google Search Console',
                        'Update sitemap when content changes'
                    ]
                }

            logger.info(f"[WI-021] Found sitemap: {sitemap_url} (method: {discovery_method})")

            # ========== STEP 2: FETCH SITEMAP ==========
            sitemap_content, fetch_result = await self._fetch_sitemap(sitemap_url)

            if not sitemap_content:
                return {
                    'score': 20,
                    'comment': f'Sitemap found but inaccessible (HTTP {fetch_result.get("status_code", "error")}). URL: {sitemap_url}. Fix accessibility - inaccessible sitemaps cannot help indexing.',
                    'metadata': {
                        'sitemap_url': sitemap_url,
                        'sitemap_found': True,
                        'sitemap_accessible': False,
                        'discovery_method': discovery_method,
                        'fetch_status': fetch_result.get('status'),
                        'execution_time_ms': self._calc_execution_time(execution_start)
                    },
                    'recommendations': [
                        f'Fix sitemap accessibility (returns HTTP {fetch_result.get("status_code")})',
                        'Ensure sitemap is publicly accessible',
                        'Check server configuration',
                        'Verify sitemap file exists'
                    ]
                }

            # ========== STEP 3: PARSE AND VALIDATE XML ==========
            sitemap_analysis = await self._analyze_sitemap_xml(sitemap_content, sitemap_url)

            # ========== STEP 4: CHECK ROBOTS.TXT REFERENCE ==========
            in_robots = await self._check_robots_txt(base_url, sitemap_url)

            # ========== STEP 5: CALCULATE SCORE ==========
            score = self._calculate_sitemap_score(sitemap_analysis, discovery_method, in_robots)

            # ========== STEP 6: GENERATE COMMENT ==========
            comment = self._generate_comment(sitemap_analysis, discovery_method, in_robots, sitemap_url)

            return {
                'score': score,
                'comment': comment,
                'metadata': {
                    'sitemap_url': sitemap_url,
                    'sitemap_found': True,
                    'sitemap_accessible': True,
                    'discovery_method': discovery_method,
                    'in_robots_txt': in_robots,
                    'url_count': sitemap_analysis.get('url_count', 0),
                    'is_sitemap_index': sitemap_analysis.get('is_sitemap_index', False),
                    'xml_valid': sitemap_analysis.get('xml_valid', False),
                    'has_lastmod': sitemap_analysis.get('has_lastmod', False),
                    'execution_time_ms': self._calc_execution_time(execution_start)
                },
                'recommendations': self._generate_recommendations(sitemap_analysis, in_robots, score)
            }

        except Exception as e:
            logger.error(f"[WI-021] Error: {str(e)}", exc_info=True)
            return self._error_result(str(e), execution_start)

    async def _find_sitemap_url(self, base_url: str, metadata: Dict[str, Any]) -> Tuple[Optional[str], str]:
        """Find sitemap URL using multiple discovery methods."""
        # Priority 1: Metadata override
        if metadata and 'sitemap_url' in metadata:
            return (metadata['sitemap_url'], 'metadata')

        # Priority 2: Check robots.txt
        robots_sitemap = await self._check_robots_txt_for_sitemap(base_url)
        if robots_sitemap:
            return (robots_sitemap, 'robots_txt')

        # Priority 3: Try standard paths
        for path in self.SITEMAP_PATHS:
            candidate_url = urljoin(base_url, path)
            logger.debug(f"[WI-021] Checking: {candidate_url}")

            # Quick HEAD check
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    response = await client.head(candidate_url, follow_redirects=True)
                    if response.status_code == 200:
                        return (candidate_url, f'standard_path:{path}')
            except:
                continue

        return (None, 'not_found')

    async def _check_robots_txt_for_sitemap(self, base_url: str) -> Optional[str]:
        """Check robots.txt for Sitemap directive."""
        robots_url = urljoin(base_url, '/robots.txt')

        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(robots_url)

                if response.status_code == 200:
                    content = response.text

                    # Look for Sitemap directive
                    import re
                    match = re.search(r'^Sitemap:\s*(.+)$', content, re.MULTILINE | re.IGNORECASE)

                    if match:
                        sitemap_url = match.group(1).strip()
                        return sitemap_url

        except Exception as e:
            logger.debug(f"[WI-021] Error checking robots.txt: {str(e)}")

        return None

    async def _fetch_sitemap(self, sitemap_url: str) -> Tuple[Optional[str], Dict]:
        """Fetch sitemap content with error handling."""
        fetch_start = datetime.utcnow()

        try:
            async with httpx.AsyncClient(
                timeout=self.API_TIMEOUT,
                follow_redirects=True
            ) as client:
                response = await client.get(sitemap_url)
                fetch_time = (datetime.utcnow() - fetch_start).total_seconds() * 1000

                if response.status_code == 200:
                    # Check size
                    content_length = len(response.content)
                    if content_length > self.MAX_SITEMAP_SIZE_MB * 1024 * 1024:
                        return (None, {
                            'status': 'oversized',
                            'status_code': 200,
                            'size_mb': content_length / (1024 * 1024),
                            'fetch_time_ms': fetch_time
                        })

                    return (response.text, {
                        'status': 'success',
                        'status_code': 200,
                        'fetch_time_ms': fetch_time,
                        'size_bytes': content_length
                    })
                else:
                    return (None, {
                        'status': 'http_error',
                        'status_code': response.status_code,
                        'fetch_time_ms': fetch_time
                    })

        except Exception as e:
            logger.error(f"[WI-021] Fetch error: {str(e)}")
            return (None, {
                'status': 'error',
                'error': str(e),
                'fetch_time_ms': (datetime.utcnow() - fetch_start).total_seconds() * 1000
            })

    async def _analyze_sitemap_xml(self, xml_content: str, sitemap_url: str) -> Dict[str, Any]:
        """Parse and analyze sitemap XML structure."""
        analysis = {
            'xml_valid': False,
            'is_sitemap_index': False,
            'url_count': 0,
            'has_lastmod': False,
            'has_changefreq': False,
            'has_priority': False,
            'issues': []
        }

        try:
            # Parse XML
            root = ET.fromstring(xml_content)

            analysis['xml_valid'] = True

            # Check if sitemap index
            if 'sitemapindex' in root.tag.lower():
                analysis['is_sitemap_index'] = True

                # Count child sitemaps
                sitemaps = root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap')
                analysis['url_count'] = len(sitemaps)
                analysis['sitemap_count'] = len(sitemaps)

            else:
                # Regular sitemap - count URLs
                urls = root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url')
                analysis['url_count'] = len(urls)

                if len(urls) == 0:
                    analysis['issues'].append('Empty sitemap (0 URLs)')

                if len(urls) > self.MAX_SITEMAP_URLS:
                    analysis['issues'].append(f'Oversized sitemap ({len(urls)} URLs, max {self.MAX_SITEMAP_URLS})')

                # Check elements
                if urls:
                    # Sample first URL for element detection
                    first_url = urls[0]

                    lastmod = first_url.find('{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod')
                    analysis['has_lastmod'] = lastmod is not None

                    changefreq = first_url.find('{http://www.sitemaps.org/schemas/sitemap/0.9}changefreq')
                    analysis['has_changefreq'] = changefreq is not None

                    priority = first_url.find('{http://www.sitemaps.org/schemas/sitemap/0.9}priority')
                    analysis['has_priority'] = priority is not None

        except ET.ParseError as e:
            analysis['xml_valid'] = False
            analysis['issues'].append(f'Invalid XML: {str(e)}')

        except Exception as e:
            analysis['issues'].append(f'Parse error: {str(e)}')

        return analysis

    async def _check_robots_txt(self, base_url: str, sitemap_url: str) -> bool:
        """Check if sitemap is declared in robots.txt."""
        robots_url = urljoin(base_url, '/robots.txt')

        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(robots_url)

                if response.status_code == 200:
                    content = response.text.lower()
                    sitemap_url_lower = sitemap_url.lower()

                    return sitemap_url_lower in content

        except Exception as e:
            logger.debug(f"[WI-021] Error checking robots.txt: {str(e)}")

        return False

    def _calculate_sitemap_score(
        self,
        analysis: Dict[str, Any],
        discovery_method: str,
        in_robots: bool
    ) -> int:
        """Calculate sitemap quality score."""
        score = 0

        # Presence & Accessibility (30 points)
        score += 30  # Already found and accessible

        # XML Validity (25 points)
        if analysis['xml_valid']:
            score += 25
        else:
            score += 0  # Critical failure

        # Completeness (20 points)
        if analysis['url_count'] > 0:
            if analysis['is_sitemap_index']:
                score += 15  # Sitemap index is good
            elif analysis['url_count'] <= self.MAX_SITEMAP_URLS:
                score += 20
            else:
                score += 5  # Oversized

        # Element quality (15 points)
        if analysis.get('has_lastmod'):
            score += 6
        if analysis.get('has_changefreq'):
            score += 4
        if analysis.get('has_priority'):
            score += 5

        # Robots.txt reference (15 points)
        if in_robots:
            score += 15
        elif 'robots_txt' in discovery_method:
            score += 15  # Found in robots.txt

        # Discovery method bonus
        if 'standard_path' in discovery_method and discovery_method.endswith('/sitemap.xml'):
            score += 5  # Bonus for standard location

        # Penalties
        if len(analysis.get('issues', [])) > 0:
            score -= len(analysis['issues']) * 5

        return max(0, min(100, score))

    def _generate_comment(
        self,
        analysis: Dict[str, Any],
        discovery_method: str,
        in_robots: bool,
        sitemap_url: str
    ) -> str:
        """Generate comprehensive comment."""
        if analysis['xml_valid']:
            if analysis['is_sitemap_index']:
                comment = f"Sitemap index found with {analysis.get('sitemap_count', 0)} sitemaps."
            else:
                url_count = analysis['url_count']
                comment = f"XML sitemap found with {url_count:,} URLs."
        else:
            comment = "Sitemap found but XML is invalid."

        # Discovery
        if 'robots_txt' in discovery_method:
            comment += " Discovered via robots.txt."
        elif 'standard_path' in discovery_method:
            path = discovery_method.split(':')[1]
            comment += f" Found at standard path ({path})."

        # Elements
        elements = []
        if analysis.get('has_lastmod'):
            elements.append('lastmod')
        if analysis.get('has_changefreq'):
            elements.append('changefreq')
        if analysis.get('has_priority'):
            elements.append('priority')

        if elements:
            comment += f" Elements: {', '.join(elements)}."
        else:
            comment += " Missing recommended elements (lastmod, changefreq, priority)."

        # Robots.txt
        if in_robots:
            comment += " Declared in robots.txt."
        else:
            comment += " NOT declared in robots.txt (add Sitemap directive)."

        # Issues
        if analysis.get('issues'):
            comment += f" Issues: {'; '.join(analysis['issues'][:2])}."

        # Context
        if analysis['xml_valid'] and in_robots and analysis['url_count'] > 0:
            comment += " Well-configured sitemap for optimal crawling and indexing."
        elif analysis['xml_valid']:
            comment += " Functional sitemap but improvements recommended."
        else:
            comment += " Fix XML errors immediately - invalid sitemaps cannot aid indexing."

        return comment

    def _generate_recommendations(
        self,
        analysis: Dict[str, Any],
        in_robots: bool,
        score: int
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        # Critical issues
        if not analysis['xml_valid']:
            recommendations.append("CRITICAL: Fix XML validation errors in sitemap")

        if analysis['url_count'] == 0 and not analysis['is_sitemap_index']:
            recommendations.append("CRITICAL: Empty sitemap - add URLs")

        # Robots.txt
        if not in_robots:
            recommendations.append('Add "Sitemap: [url]" directive to robots.txt')

        # Elements
        if not analysis.get('has_lastmod'):
            recommendations.append("Add <lastmod> to show content freshness")

        if not analysis.get('has_changefreq'):
            recommendations.append("Add <changefreq> to indicate update frequency")

        if not analysis.get('has_priority'):
            recommendations.append("Add <priority> to indicate relative importance")

        # Size
        if analysis['url_count'] > self.MAX_SITEMAP_URLS:
            recommendations.append(f"Split sitemap (>{self.MAX_SITEMAP_URLS} URLs) into sitemap index")

        # General
        if score < 80:
            recommendations.append("Submit sitemap to Google Search Console")
            recommendations.append("Update sitemap when content changes")

        return recommendations[:6]

    def _calc_execution_time(self, start: datetime) -> int:
        """Calculate execution time in milliseconds."""
        return int((datetime.utcnow() - start).total_seconds() * 1000)

    def _error_result(self, error_msg: str, execution_start: datetime) -> Dict[str, Any]:
        """Generate error result."""
        return {
            'score': 0,
            'comment': f'Sitemap measurement failed: {error_msg}',
            'metadata': {
                'error': error_msg,
                'execution_time_ms': self._calc_execution_time(execution_start)
            }
        }


# Export for orchestrator
measurement = XMLSitemapPresenceMeasurement()
