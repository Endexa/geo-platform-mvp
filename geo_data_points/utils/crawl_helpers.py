"""
Web Crawling Utilities

Site crawling, link analysis, redirect chains, broken link detection,
and internal linking structure analysis.
"""

from typing import List, Dict, Any, Set, Optional, Tuple
from urllib.parse import urlparse, urljoin
from collections import defaultdict, deque
import re

from .logging import get_logger
from .http_client import fetch_url, follow_redirects, get_http_session


logger = get_logger("crawl_helpers")


class SiteCrawler:
    """
    Lightweight site crawler for internal link analysis.

    Optimized for billions of daily operations.
    """

    def __init__(self, start_url: str, max_pages: int = 100, max_depth: int = 5):
        """
        Initialize crawler.

        Args:
            start_url: Starting URL
            max_pages: Maximum pages to crawl
            max_depth: Maximum click depth from start
        """
        self.start_url = start_url
        self.max_pages = max_pages
        self.max_depth = max_depth

        parsed = urlparse(start_url)
        self.base_domain = parsed.netloc

        self.visited: Set[str] = set()
        self.to_visit: deque = deque([(start_url, 0)])  # (url, depth)
        self.pages: Dict[str, Dict[str, Any]] = {}
        self.internal_links: Dict[str, List[str]] = defaultdict(list)

    def crawl(self) -> Dict[str, Any]:
        """
        Perform crawl.

        Returns:
            Crawl results with pages, links, and metrics
        """
        while self.to_visit and len(self.visited) < self.max_pages:
            url, depth = self.to_visit.popleft()

            if url in self.visited or depth > self.max_depth:
                continue

            self._crawl_page(url, depth)

        return self._generate_report()

    def _crawl_page(self, url: str, depth: int):
        """Crawl a single page."""
        self.visited.add(url)

        response = fetch_url(url, use_cache=False)
        if not response:
            self.pages[url] = {
                'status': 'error',
                'depth': depth,
                'links': []
            }
            return

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(response.text, 'lxml')
        links = []

        # Extract all links
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href'].strip()

            # Resolve relative URLs
            absolute_url = urljoin(url, href)

            # Check if internal
            if self._is_internal(absolute_url):
                links.append(absolute_url)

                # Add to queue if not visited
                if absolute_url not in self.visited:
                    self.to_visit.append((absolute_url, depth + 1))

        self.pages[url] = {
            'status': 'success',
            'status_code': response.status_code,
            'depth': depth,
            'links': links,
            'title': soup.find('title').string if soup.find('title') else ''
        }

        self.internal_links[url] = links

    def _is_internal(self, url: str) -> bool:
        """Check if URL is internal."""
        parsed = urlparse(url)
        return parsed.netloc == self.base_domain or parsed.netloc == ''

    def _generate_report(self) -> Dict[str, Any]:
        """Generate crawl report."""
        total_pages = len(self.visited)
        successful = sum(1 for p in self.pages.values() if p['status'] == 'success')

        # Calculate average depth
        depths = [p['depth'] for p in self.pages.values() if p['status'] == 'success']
        avg_depth = sum(depths) / len(depths) if depths else 0

        # Find orphan pages (no internal links pointing to them)
        linked_pages = set()
        for links in self.internal_links.values():
            linked_pages.update(links)

        orphan_pages = [url for url in self.visited if url not in linked_pages and url != self.start_url]

        return {
            'total_pages': total_pages,
            'successful_crawls': successful,
            'failed_crawls': total_pages - successful,
            'average_depth': round(avg_depth, 2),
            'max_depth_reached': max(depths) if depths else 0,
            'orphan_pages': orphan_pages,
            'orphan_count': len(orphan_pages),
            'pages': self.pages,
            'internal_links': dict(self.internal_links)
        }

    def find_broken_links(self) -> List[Dict[str, Any]]:
        """
        Find broken internal links (404s).

        Returns:
            List of broken links with source pages
        """
        broken = []

        for source_url, target_urls in self.internal_links.items():
            for target_url in target_urls:
                if target_url in self.pages:
                    page_data = self.pages[target_url]

                    if page_data['status'] == 'error' or page_data.get('status_code', 200) >= 400:
                        broken.append({
                            'source': source_url,
                            'target': target_url,
                            'status_code': page_data.get('status_code', 0)
                        })

        return broken

    def calculate_internal_pagerank(self, iterations: int = 20, damping: float = 0.85) -> Dict[str, float]:
        """
        Calculate simplified PageRank for internal pages.

        Args:
            iterations: Number of iterations
            damping: Damping factor (0.85 standard)

        Returns:
            Dict of URL -> PageRank score
        """
        pages = list(self.visited)
        n = len(pages)

        if n == 0:
            return {}

        # Initialize PageRank
        pagerank = {url: 1.0 / n for url in pages}

        for _ in range(iterations):
            new_pagerank = {}

            for page in pages:
                rank_sum = 0.0

                # Find all pages linking to this page
                for source_url, targets in self.internal_links.items():
                    if page in targets:
                        outbound_count = len(targets)
                        if outbound_count > 0:
                            rank_sum += pagerank[source_url] / outbound_count

                new_pagerank[page] = (1 - damping) / n + damping * rank_sum

            pagerank = new_pagerank

        return pagerank


def detect_redirect_chains(url: str) -> Dict[str, Any]:
    """
    Detect and analyze redirect chains.

    Args:
        url: Starting URL

    Returns:
        {
            'has_redirects': bool,
            'chain_length': int,
            'final_url': str,
            'redirects': List[Dict],
            'is_loop': bool
        }
    """
    redirects = follow_redirects(url, max_hops=10)

    chain_length = len(redirects)
    has_redirects = chain_length > 1

    # Check for redirect loop
    urls_in_chain = [r['url'] for r in redirects]
    is_loop = len(urls_in_chain) != len(set(urls_in_chain))

    final_url = redirects[-1]['url'] if redirects else url

    return {
        'has_redirects': has_redirects,
        'chain_length': chain_length,
        'final_url': final_url,
        'redirects': redirects,
        'is_loop': is_loop
    }


def calculate_click_depth(start_url: str, max_pages: int = 50) -> Dict[str, int]:
    """
    Calculate click depth for pages from homepage.

    Args:
        start_url: Homepage URL
        max_pages: Max pages to analyze

    Returns:
        Dict of URL -> click depth
    """
    crawler = SiteCrawler(start_url, max_pages=max_pages, max_depth=5)
    crawler.crawl()

    depths = {}
    for url, data in crawler.pages.items():
        if data['status'] == 'success':
            depths[url] = data['depth']

    return depths


def analyze_internal_linking(start_url: str, max_pages: int = 50) -> Dict[str, Any]:
    """
    Comprehensive internal linking analysis.

    Args:
        start_url: Homepage URL
        max_pages: Max pages to analyze

    Returns:
        {
            'total_pages': int,
            'average_internal_links': float,
            'pages_with_no_internal_links': int,
            'orphan_pages': List[str],
            'pagerank_scores': Dict[str, float],
            'broken_links': List[Dict]
        }
    """
    crawler = SiteCrawler(start_url, max_pages=max_pages, max_depth=5)
    report = crawler.crawl()

    # Calculate average internal links
    link_counts = [len(links) for links in crawler.internal_links.values()]
    avg_links = sum(link_counts) / len(link_counts) if link_counts else 0

    # Pages with no outbound links
    pages_no_links = sum(1 for count in link_counts if count == 0)

    # Calculate PageRank
    pagerank = crawler.calculate_internal_pagerank()

    # Find broken links
    broken = crawler.find_broken_links()

    return {
        'total_pages': report['total_pages'],
        'average_internal_links': round(avg_links, 2),
        'pages_with_no_internal_links': pages_no_links,
        'orphan_pages': report['orphan_pages'],
        'orphan_count': report['orphan_count'],
        'pagerank_scores': pagerank,
        'broken_links': broken,
        'broken_link_count': len(broken)
    }
