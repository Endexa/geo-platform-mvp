"""
BV-003: Wikipedia Page Presence

Checks if entity has a Wikipedia page with backlinks count.
Wikipedia presence is a strong authority and notability signal for AI models.
"""

from typing import Dict, Any
from geo_data_points.base import BaseMeasurement
from geo_data_points.utils.external_apis import WikipediaClient
from loguru import logger


class WikipediaPresenceMeasurement(BaseMeasurement):
    """Check Wikipedia page presence and backlinks."""

    def __init__(self):
        super().__init__(
            code="BV-003",
            name="Wikipedia Page Presence",
            description="Checks if entity has Wikipedia page with backlinks for authority signals",
            category="Brand Visibility",
            weight=0.95  # Very high importance for authority
        )
        self.wiki_client = WikipediaClient()

    async def measure(self, url: str, html: str = None, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Measure Wikipedia presence and authority.

        Scoring:
        - 100: Wikipedia page + 100+ backlinks (high notability)
        - 90: Wikipedia page + 50-100 backlinks
        - 80: Wikipedia page + 20-50 backlinks
        - 70: Wikipedia page + 10-20 backlinks
        - 60: Wikipedia page + 5-10 backlinks
        - 50: Wikipedia page + 1-5 backlinks
        - 40: Wikipedia page but no backlinks
        - 0: No Wikipedia page

        Args:
            url: Target URL to analyze
            html: Unused
            metadata: Should contain 'brand_name' or will extract from URL

        Returns:
            Dict with score (0-100) and detailed comment
        """
        try:
            # Extract brand/entity name from metadata or URL
            if metadata and 'brand_name' in metadata:
                query = metadata['brand_name']
            else:
                # Extract domain name as query
                from urllib.parse import urlparse
                parsed = urlparse(url)
                domain = parsed.netloc.replace('www.', '')
                query = domain.split('.')[0].title()

            # Search for Wikipedia page
            wiki_page = self.wiki_client.search_page(query)

            if not wiki_page:
                return {
                    'score': 0,
                    'comment': f'No Wikipedia page found for "{query}". Wikipedia presence is a strong authority signal for AI models. Recommendation: If entity meets Wikipedia notability guidelines, create a well-sourced Wikipedia article. This significantly boosts AI model citation preference and brand credibility.'
                }

            # Extract page details
            page_title = wiki_page.get('title', query)
            page_url = wiki_page.get('url', '')
            page_id = wiki_page.get('pageid', 0)
            summary = wiki_page.get('summary', '')

            # Get backlinks count (how many Wikipedia pages link to this page)
            backlinks_count = self.wiki_client.get_backlinks_count(page_title)

            if backlinks_count is None:
                # Page found but couldn't get backlinks
                return {
                    'score': 40,
                    'comment': f'Wikipedia page found: "{page_title}" ({page_url}). Cannot retrieve backlinks count. Good authority signal but verify page quality.'
                }

            # ========== SCORING BASED ON BACKLINKS ==========
            if backlinks_count >= 100:
                score = 100
                notability = "Exceptional notability"
                comment = f'{notability}: Wikipedia page "{page_title}" with {backlinks_count:,}+ backlinks! Outstanding authority signal for AI models. Extremely strong citation preference.'
            elif backlinks_count >= 50:
                score = 90
                notability = "Very high notability"
                comment = f'{notability}: Wikipedia page "{page_title}" with {backlinks_count} backlinks. Excellent authority signal for AI models. Strong citation preference.'
            elif backlinks_count >= 20:
                score = 80
                notability = "High notability"
                comment = f'{notability}: Wikipedia page "{page_title}" with {backlinks_count} backlinks. Strong authority signal for AI citation.'
            elif backlinks_count >= 10:
                score = 70
                notability = "Good notability"
                comment = f'{notability}: Wikipedia page "{page_title}" with {backlinks_count} backlinks. Good authority signal.'
            elif backlinks_count >= 5:
                score = 60
                notability = "Moderate notability"
                comment = f'{notability}: Wikipedia page "{page_title}" with {backlinks_count} backlinks. Moderate authority signal.'
            elif backlinks_count >= 1:
                score = 50
                notability = "Emerging notability"
                comment = f'{notability}: Wikipedia page "{page_title}" with {backlinks_count} backlink(s). Basic authority signal. Expand page and increase internal links.'
            else:
                score = 40
                notability = "Limited notability"
                comment = f'{notability}: Wikipedia page "{page_title}" exists but has no backlinks. Limited authority signal. Add references to page from related Wikipedia articles.'

            # Add page URL
            comment += f' Page: {page_url}.'

            # Add summary snippet if available
            if summary and len(summary) > 50:
                summary_snippet = summary[:150] + '...' if len(summary) > 150 else summary
                comment += f' Summary: "{summary_snippet}"'

            # ========== RECOMMENDATIONS ==========
            recommendations = []

            if backlinks_count < 50:
                recommendations.append('Expand Wikipedia content with more references')
                recommendations.append('Link from related Wikipedia pages')
                recommendations.append('Ensure citations to reliable sources')

            if backlinks_count < 10:
                recommendations.append('Add more context and notable achievements')
                recommendations.append('Participate in WikiProject relevant to your domain')

            if recommendations:
                comment += f' Improvements: {"; ".join(recommendations[:2])}.'

            # Authority context
            if score >= 80:
                comment += ' Wikipedia presence with strong backlinks significantly boosts AI model citation preference.'
            elif score >= 60:
                comment += ' Wikipedia presence provides good authority signal for AI models.'
            else:
                comment += ' Wikipedia page exists but limited authority signals. Expand and build connections.'

            return {
                'score': score,
                'comment': comment,
                'metadata': {
                    'wikipedia_url': page_url,
                    'wikipedia_title': page_title,
                    'backlinks_count': backlinks_count,
                    'page_id': page_id
                }
            }

        except Exception as e:
            logger.error(f"Error checking Wikipedia presence for {url}: {str(e)}")
            return {
                'score': 0,
                'comment': f'Wikipedia check failed: {str(e)}'
            }


# Export for orchestrator
measurement = WikipediaPresenceMeasurement()
