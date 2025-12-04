"""
WI-010: Sitemap - Lastmod Coverage

Analyzes XML sitemap for lastmod tag coverage and accuracy.
The lastmod tag helps AI crawlers prioritize fresh content for indexing.
"""

from typing import Dict, Any
from geo_data_points.base import BaseMeasurement
from geo_data_points.utils.http_client import CachedSession
from geo_data_points.utils.seo_helpers import SitemapAnalyzer
from datetime import datetime, timedelta
from loguru import logger


class SitemapLastmodCoverageMeasurement(BaseMeasurement):
    """Measure lastmod tag coverage and freshness in XML sitemap."""

    def __init__(self):
        super().__init__(
            code="WI-010",
            name="Sitemap - Lastmod Coverage",
            description="Analyzes lastmod tag coverage and accuracy in XML sitemap",
            category="Web Infrastructure",
            weight=0.75  # Important for AI crawler prioritization
        )
        self.session = CachedSession()

    async def measure(self, url: str, html: str = None, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Measure lastmod tag coverage and quality.

        Scoring:
        - 100: >90% URLs have valid, recent lastmod tags
        - 80: 70-90% coverage with valid dates
        - 60: 50-70% coverage
        - 40: 30-50% coverage
        - 20: <30% coverage
        - 0: No sitemap or no lastmod tags

        Args:
            url: Target URL to analyze
            html: Unused (sitemap is fetched directly)
            metadata: Unused

        Returns:
            Dict with score (0-100) and detailed comment
        """
        try:
            # Extract domain from URL
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = f"{parsed.scheme}://{parsed.netloc}"

            # Try common sitemap locations
            sitemap_urls = [
                f"{domain}/sitemap.xml",
                f"{domain}/sitemap_index.xml",
                f"{domain}/sitemap-index.xml",
                f"{domain}/sitemap1.xml"
            ]

            sitemap_content = None
            sitemap_url = None

            for surl in sitemap_urls:
                try:
                    response = self.session.get(surl, timeout=10)
                    if response.status_code == 200 and 'xml' in response.headers.get('content-type', '').lower():
                        sitemap_content = response.text
                        sitemap_url = surl
                        break
                except:
                    continue

            if not sitemap_content:
                # Try robots.txt to find sitemap
                try:
                    robots_response = self.session.get(f"{domain}/robots.txt")
                    if robots_response.status_code == 200:
                        for line in robots_response.text.split('\n'):
                            if line.lower().startswith('sitemap:'):
                                sitemap_url = line.split(':', 1)[1].strip()
                                response = self.session.get(sitemap_url, timeout=10)
                                if response.status_code == 200:
                                    sitemap_content = response.text
                                    break
                except:
                    pass

            if not sitemap_content:
                return {
                    'score': 0,
                    'comment': 'No XML sitemap found. AI crawlers cannot efficiently discover and prioritize your content. Create /sitemap.xml with lastmod tags for optimal indexing.'
                }

            # Parse sitemap
            analyzer = SitemapAnalyzer(sitemap_content)
            lastmod_stats = analyzer.get_lastmod_coverage()

            if lastmod_stats['error']:
                return {
                    'score': 0,
                    'comment': f'Sitemap parsing error: {lastmod_stats["error"]}. Ensure valid XML format.'
                }

            total_urls = lastmod_stats['total_urls']
            lastmod_count = lastmod_stats['lastmod_count']
            coverage_percentage = lastmod_stats['coverage_percentage']

            if total_urls == 0:
                return {
                    'score': 0,
                    'comment': 'Sitemap is empty (0 URLs). Add URLs with lastmod tags for AI crawler prioritization.'
                }

            # Analyze lastmod freshness
            recent_updates = 0
            valid_dates = 0
            now = datetime.utcnow()

            if 'lastmod_dates' in lastmod_stats:
                for date_str in lastmod_stats['lastmod_dates']:
                    try:
                        # Parse ISO 8601 date
                        if 'T' in date_str:
                            lastmod_date = datetime.fromisoformat(date_str.replace('Z', '+00:00')).replace(tzinfo=None)
                        else:
                            lastmod_date = datetime.strptime(date_str, '%Y-%m-%d')

                        valid_dates += 1

                        # Check if updated in last 90 days
                        if (now - lastmod_date).days <= 90:
                            recent_updates += 1
                    except:
                        pass

            # Calculate score
            score = 0
            comment_parts = []

            # Base score from coverage
            if coverage_percentage >= 90:
                score = 90
                comment_parts.append(f"Excellent lastmod coverage: {coverage_percentage:.1f}% ({lastmod_count}/{total_urls} URLs)")
            elif coverage_percentage >= 70:
                score = 70
                comment_parts.append(f"Good lastmod coverage: {coverage_percentage:.1f}% ({lastmod_count}/{total_urls} URLs)")
            elif coverage_percentage >= 50:
                score = 50
                comment_parts.append(f"Moderate lastmod coverage: {coverage_percentage:.1f}% ({lastmod_count}/{total_urls} URLs)")
            elif coverage_percentage >= 30:
                score = 30
                comment_parts.append(f"Low lastmod coverage: {coverage_percentage:.1f}% ({lastmod_count}/{total_urls} URLs)")
            else:
                score = 10
                comment_parts.append(f"Very low lastmod coverage: {coverage_percentage:.1f}% ({lastmod_count}/{total_urls} URLs)")

            # Bonus for freshness
            if valid_dates > 0:
                freshness_percentage = (recent_updates / valid_dates) * 100
                if freshness_percentage >= 50:
                    score = min(100, score + 10)
                    comment_parts.append(f"{freshness_percentage:.0f}% URLs updated in last 90 days (fresh content)")
                else:
                    comment_parts.append(f"Only {freshness_percentage:.0f}% URLs updated recently - consider more frequent updates")

            # Add recommendations
            if coverage_percentage < 90:
                comment_parts.append(f"Add lastmod tags to {total_urls - lastmod_count} more URLs for better AI crawler prioritization")

            if valid_dates > 0 and recent_updates == 0:
                comment_parts.append("WARNING: No recent updates detected - AI crawlers may deprioritize your content")

            return {
                'score': score,
                'comment': '. '.join(comment_parts) + '.'
            }

        except Exception as e:
            logger.error(f"Error measuring sitemap lastmod coverage for {url}: {str(e)}")
            return {
                'score': 0,
                'comment': f'Measurement failed: {str(e)}'
            }


# Export for orchestrator
measurement = SitemapLastmodCoverageMeasurement()
