"""
HTML Parsing Utilities

Advanced HTML parsing, DOM analysis, and content extraction
optimized for billions of daily operations.
"""

from bs4 import BeautifulSoup, Tag, NavigableString
from typing import List, Dict, Any, Optional, Set, Tuple
import re
from urllib.parse import urljoin, urlparse
from functools import lru_cache

from .logging import get_logger
from .http_client import fetch_url


logger = get_logger("html_parser")


class HTMLAnalyzer:
    """Advanced HTML parsing and analysis."""

    def __init__(self, html: str, base_url: str = ""):
        """
        Initialize HTML analyzer.

        Args:
            html: HTML content
            base_url: Base URL for resolving relative links
        """
        self.html = html
        self.base_url = base_url
        self.soup = BeautifulSoup(html, 'lxml')  # lxml is faster than html.parser

    @classmethod
    def from_url(cls, url: str) -> Optional['HTMLAnalyzer']:
        """Create analyzer from URL."""
        response = fetch_url(url)
        if not response:
            return None

        return cls(response.text, url)

    # ========== Meta Tags ==========

    def get_meta_tags(self) -> Dict[str, str]:
        """Extract all meta tags."""
        meta_tags = {}

        for meta in self.soup.find_all('meta'):
            # name attribute
            if meta.get('name'):
                meta_tags[meta['name']] = meta.get('content', '')

            # property attribute (Open Graph, etc.)
            if meta.get('property'):
                meta_tags[meta['property']] = meta.get('content', '')

            # http-equiv
            if meta.get('http-equiv'):
                meta_tags[f"http-equiv-{meta['http-equiv']}"] = meta.get('content', '')

        return meta_tags

    def get_title(self) -> str:
        """Extract page title."""
        title_tag = self.soup.find('title')
        return title_tag.string.strip() if title_tag and title_tag.string else ""

    def get_meta_description(self) -> str:
        """Extract meta description."""
        meta = self.soup.find('meta', attrs={'name': 'description'})
        return meta.get('content', '').strip() if meta else ""

    def get_canonical_url(self) -> str:
        """Extract canonical URL."""
        canonical = self.soup.find('link', rel='canonical')
        return canonical.get('href', '').strip() if canonical else ""

    def get_og_tags(self) -> Dict[str, str]:
        """Extract Open Graph tags."""
        og_tags = {}
        for meta in self.soup.find_all('meta', property=re.compile(r'^og:')):
            prop = meta.get('property', '')
            og_tags[prop] = meta.get('content', '')
        return og_tags

    def get_twitter_card_tags(self) -> Dict[str, str]:
        """Extract Twitter Card tags."""
        twitter_tags = {}
        for meta in self.soup.find_all('meta', attrs={'name': re.compile(r'^twitter:')}):
            name = meta.get('name', '')
            twitter_tags[name] = meta.get('content', '')
        return twitter_tags

    # ========== Headings ==========

    def get_headings(self, levels: Optional[List[int]] = None) -> Dict[str, List[str]]:
        """
        Extract headings by level.

        Args:
            levels: List of levels to extract (1-6), or None for all

        Returns:
            Dict with keys 'h1', 'h2', etc.
        """
        if levels is None:
            levels = [1, 2, 3, 4, 5, 6]

        headings = {}
        for level in levels:
            tag = f'h{level}'
            headings[tag] = [h.get_text(strip=True) for h in self.soup.find_all(tag)]

        return headings

    def validate_heading_hierarchy(self) -> Dict[str, Any]:
        """
        Validate logical heading hierarchy.

        Returns:
            {
                'is_valid': bool,
                'issues': List[str],
                'structure': List[tuple[level, text]]
            }
        """
        issues = []
        structure = []

        # Extract all headings in order
        for heading in self.soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            level = int(heading.name[1])
            text = heading.get_text(strip=True)
            structure.append((level, text))

        # Validation rules
        h1_count = len([h for h in structure if h[0] == 1])
        if h1_count == 0:
            issues.append("Missing H1 tag")
        elif h1_count > 1:
            issues.append(f"Multiple H1 tags ({h1_count})")

        # Check for skipped levels
        for i in range(1, len(structure)):
            prev_level = structure[i-1][0]
            curr_level = structure[i][0]

            if curr_level > prev_level + 1:
                issues.append(f"Skipped heading level: H{prev_level} to H{curr_level}")

        return {
            'is_valid': len(issues) == 0,
            'issues': issues,
            'structure': structure,
            'h1_count': h1_count
        }

    # ========== Links ==========

    def get_links(self, internal_only: bool = False, external_only: bool = False) -> List[Dict[str, str]]:
        """
        Extract all links.

        Returns:
            List of dicts with 'href', 'text', 'type' (internal/external)
        """
        links = []

        for a_tag in self.soup.find_all('a', href=True):
            href = a_tag['href'].strip()
            text = a_tag.get_text(strip=True)

            # Resolve relative URLs
            absolute_url = urljoin(self.base_url, href)

            # Determine if internal or external
            is_internal = self._is_internal_link(absolute_url)

            if internal_only and not is_internal:
                continue
            if external_only and is_internal:
                continue

            links.append({
                'href': absolute_url,
                'text': text,
                'type': 'internal' if is_internal else 'external',
                'nofollow': 'nofollow' in a_tag.get('rel', [])
            })

        return links

    def _is_internal_link(self, url: str) -> bool:
        """Check if link is internal."""
        if not self.base_url:
            return False

        base_domain = urlparse(self.base_url).netloc
        link_domain = urlparse(url).netloc

        return base_domain == link_domain or link_domain == ''

    def count_external_links(self) -> int:
        """Count external links."""
        return len(self.get_links(external_only=True))

    def count_internal_links(self) -> int:
        """Count internal links."""
        return len(self.get_links(internal_only=True))

    # ========== Images ==========

    def get_images(self) -> List[Dict[str, str]]:
        """Extract all images with metadata."""
        images = []

        for img in self.soup.find_all('img'):
            images.append({
                'src': urljoin(self.base_url, img.get('src', '')),
                'alt': img.get('alt', ''),
                'title': img.get('title', ''),
                'width': img.get('width', ''),
                'height': img.get('height', ''),
                'loading': img.get('loading', '')
            })

        return images

    def get_alt_text_coverage(self) -> Dict[str, Any]:
        """Calculate alt text coverage for images."""
        images = self.get_images()
        total = len(images)

        if total == 0:
            return {
                'coverage_percent': 100.0,
                'total_images': 0,
                'images_with_alt': 0,
                'images_without_alt': 0
            }

        with_alt = sum(1 for img in images if img['alt'].strip())
        without_alt = total - with_alt

        return {
            'coverage_percent': (with_alt / total) * 100,
            'total_images': total,
            'images_with_alt': with_alt,
            'images_without_alt': without_alt,
            'missing_alt_srcs': [img['src'] for img in images if not img['alt'].strip()][:10]
        }

    # ========== Structured Content ==========

    def get_lists(self) -> Dict[str, int]:
        """Count different list types."""
        return {
            'ul': len(self.soup.find_all('ul')),
            'ol': len(self.soup.find_all('ol')),
            'dl': len(self.soup.find_all('dl'))
        }

    def get_tables(self) -> List[Dict[str, Any]]:
        """Extract table information."""
        tables = []

        for table in self.soup.find_all('table'):
            rows = table.find_all('tr')
            headers = [th.get_text(strip=True) for th in table.find_all('th')]

            tables.append({
                'row_count': len(rows),
                'column_count': len(headers) if headers else 0,
                'headers': headers,
                'has_caption': table.find('caption') is not None
            })

        return tables

    def get_list_table_density(self) -> float:
        """
        Calculate structured content density.

        Returns percentage of content in lists/tables.
        """
        lists = self.soup.find_all(['ul', 'ol', 'table'])
        total_text = len(self.get_clean_text())

        if total_text == 0:
            return 0.0

        structured_text = sum(len(elem.get_text()) for elem in lists)

        return (structured_text / total_text) * 100

    # ========== Content Extraction ==========

    def get_clean_text(self, remove_scripts: bool = True) -> str:
        """
        Extract clean text content.

        Args:
            remove_scripts: Remove script/style tags

        Returns:
            Clean text
        """
        # Clone soup to avoid modifying original
        soup_copy = BeautifulSoup(self.html, 'lxml')

        if remove_scripts:
            for tag in soup_copy(['script', 'style', 'noscript', 'iframe']):
                tag.decompose()

        # Get text
        text = soup_copy.get_text(separator=' ', strip=True)

        # Clean whitespace
        text = re.sub(r'\s+', ' ', text)

        return text.strip()

    def get_text_by_selector(self, selector: str) -> List[str]:
        """Extract text from elements matching CSS selector."""
        elements = self.soup.select(selector)
        return [elem.get_text(strip=True) for elem in elements]

    def get_main_content(self) -> str:
        """
        Extract main content (heuristic-based).

        Prioritizes: <main>, <article>, largest content block.
        """
        # Try semantic HTML5 tags
        main_tag = self.soup.find('main')
        if main_tag:
            return main_tag.get_text(separator=' ', strip=True)

        article_tag = self.soup.find('article')
        if article_tag:
            return article_tag.get_text(separator=' ', strip=True)

        # Find largest content block
        content_tags = self.soup.find_all(['div', 'section'], class_=re.compile(r'(content|main|article|post|entry)', re.I))

        if content_tags:
            largest = max(content_tags, key=lambda tag: len(tag.get_text()))
            return largest.get_text(separator=' ', strip=True)

        # Fallback to body
        body = self.soup.find('body')
        return body.get_text(separator=' ', strip=True) if body else ""

    # ========== Schema / JSON-LD ==========

    def get_json_ld(self) -> List[Dict[str, Any]]:
        """Extract all JSON-LD structured data."""
        import json

        json_ld_scripts = self.soup.find_all('script', type='application/ld+json')
        schemas = []

        for script in json_ld_scripts:
            try:
                data = json.loads(script.string)

                # Handle both single objects and arrays
                if isinstance(data, dict):
                    schemas.append(data)
                elif isinstance(data, list):
                    schemas.extend(data)

            except (json.JSONDecodeError, AttributeError, TypeError):
                continue

        return schemas

    def find_schema_by_type(self, schema_type: str) -> List[Dict[str, Any]]:
        """
        Find all schemas of a specific type.

        Args:
            schema_type: e.g., 'Organization', 'FAQPage', 'HowTo'

        Returns:
            List of matching schemas
        """
        schemas = self.get_json_ld()
        matches = []

        for schema in schemas:
            # Handle single @type
            if schema.get('@type') == schema_type:
                matches.append(schema)

            # Handle array of @type
            elif isinstance(schema.get('@type'), list) and schema_type in schema.get('@type'):
                matches.append(schema)

        return matches

    # ========== Forms & Interactivity ==========

    def get_forms(self) -> List[Dict[str, Any]]:
        """Extract form information."""
        forms = []

        for form in self.soup.find_all('form'):
            inputs = form.find_all('input')

            forms.append({
                'action': form.get('action', ''),
                'method': form.get('method', 'get').upper(),
                'input_count': len(inputs),
                'has_captcha': bool(form.find(class_=re.compile(r'captcha', re.I)))
            })

        return forms

    # ========== Video & Media ==========

    def has_video_content(self) -> Dict[str, Any]:
        """Check for video content."""
        youtube_embeds = len(self.soup.find_all('iframe', src=re.compile(r'youtube\.com|youtu\.be')))
        vimeo_embeds = len(self.soup.find_all('iframe', src=re.compile(r'vimeo\.com')))
        video_tags = len(self.soup.find_all('video'))

        total = youtube_embeds + vimeo_embeds + video_tags

        return {
            'has_video': total > 0,
            'youtube_embeds': youtube_embeds,
            'vimeo_embeds': vimeo_embeds,
            'native_video_tags': video_tags,
            'total_videos': total
        }

    # ========== Technical SEO ==========

    def get_hreflang_tags(self) -> List[Dict[str, str]]:
        """Extract hreflang tags."""
        hreflang = []

        for link in self.soup.find_all('link', rel='alternate', hreflang=True):
            hreflang.append({
                'hreflang': link.get('hreflang'),
                'href': link.get('href', '')
            })

        return hreflang

    def get_pagination_links(self) -> Dict[str, str]:
        """Extract rel=prev/next pagination links."""
        prev_link = self.soup.find('link', rel='prev')
        next_link = self.soup.find('link', rel='next')

        return {
            'prev': prev_link.get('href', '') if prev_link else '',
            'next': next_link.get('href', '') if next_link else ''
        }

    def check_mobile_viewport(self) -> bool:
        """Check if mobile viewport meta tag exists."""
        viewport = self.soup.find('meta', attrs={'name': 'viewport'})
        return viewport is not None

    def get_favicon_url(self) -> str:
        """Extract favicon URL."""
        # Check for icon link
        icon = self.soup.find('link', rel=re.compile(r'icon', re.I))
        if icon:
            return urljoin(self.base_url, icon.get('href', ''))

        # Default favicon location
        return urljoin(self.base_url, '/favicon.ico')

    # ========== Metrics ==========

    def get_text_to_html_ratio(self) -> float:
        """Calculate text to HTML code ratio."""
        text_length = len(self.get_clean_text())
        html_length = len(self.html)

        if html_length == 0:
            return 0.0

        return (text_length / html_length) * 100

    def get_dom_size(self) -> int:
        """Count total number of DOM elements."""
        return len(self.soup.find_all())


def parse_html(html: str, base_url: str = "") -> HTMLAnalyzer:
    """
    Parse HTML and return analyzer.

    Args:
        html: HTML content
        base_url: Base URL for resolving links

    Returns:
        HTMLAnalyzer instance
    """
    return HTMLAnalyzer(html, base_url)
