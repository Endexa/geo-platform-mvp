"""
WI-015: Internal Linking Structure

Analyzes internal linking structure and distribution.
Strong internal linking helps AI crawlers discover and understand site content.
"""

from typing import Dict, Any
from geo_data_points.base import BaseMeasurement
from geo_data_points.utils.html_parser import HTMLAnalyzer
from loguru import logger


class InternalLinkingMeasurement(BaseMeasurement):
    """Analyze internal linking structure."""

    def __init__(self):
        super().__init__(
            code="WI-015",
            name="Internal Linking Structure",
            description="Analyzes internal linking structure and distribution",
            category="Web Infrastructure",
            weight=0.75  # Important for site crawlability
        )

    async def measure(self, url: str, html: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Measure internal linking quality.

        Scoring:
        - 100: 10+ internal links, good anchor text diversity
        - 90: 7-10 internal links
        - 80: 5-7 internal links
        - 70: 3-5 internal links
        - 50: 1-3 internal links
        - 0: No internal links

        Args:
            url: Target URL to analyze
            html: HTML content to parse
            metadata: Unused

        Returns:
            Dict with score (0-100) and detailed comment
        """
        try:
            if not html:
                return {
                    'score': 0,
                    'comment': 'No HTML content provided for analysis.'
                }

            analyzer = HTMLAnalyzer(html, url)

            # Get internal links
            internal_links = analyzer.get_internal_links()

            if not internal_links:
                return {
                    'score': 0,
                    'comment': 'No internal links found. Add internal links to help AI crawlers discover related content. Internal linking is crucial for site architecture and content discovery.'
                }

            link_count = len(internal_links)

            # Calculate score based on count
            if link_count >= 10:
                score = 90
                comment = f'Excellent internal linking: {link_count} internal links found. Great for AI crawler discovery!'
            elif link_count >= 7:
                score = 85
                comment = f'Good internal linking: {link_count} internal links found. Solid site architecture.'
            elif link_count >= 5:
                score = 75
                comment = f'Decent internal linking: {link_count} internal links found. Consider adding more contextual links.'
            elif link_count >= 3:
                score = 65
                comment = f'Moderate internal linking: {link_count} internal links found. Add more links to improve discoverability.'
            else:
                score = 40
                comment = f'Poor internal linking: Only {link_count} internal link(s) found. Critical: Add more internal links for AI crawler navigation.'

            # Check link diversity (unique destinations)
            unique_destinations = len(set(internal_links))
            diversity_ratio = unique_destinations / link_count if link_count > 0 else 0

            if diversity_ratio >= 0.8:
                score = min(100, score + 10)
                comment += f' High link diversity ({unique_destinations} unique destinations).'
            elif diversity_ratio >= 0.5:
                comment += f' Moderate link diversity ({unique_destinations} unique destinations).'
            else:
                score = max(0, score - 10)
                comment += f' Low link diversity ({unique_destinations} unique destinations) - avoid repetitive linking.'

            # Check for navigation links (header/footer)
            nav_links = analyzer.get_navigation_links()
            if nav_links:
                comment += f' Navigation structure found ({len(nav_links)} nav links).'

            # Recommendations
            if link_count < 7:
                comment += ' Tip: Add contextual links to related content, key pages, and topic clusters.'

            return {
                'score': score,
                'comment': comment
            }

        except Exception as e:
            logger.error(f"Error measuring internal linking for {url}: {str(e)}")
            return {
                'score': 0,
                'comment': f'Measurement failed: {str(e)}'
            }


# Export for orchestrator
measurement = InternalLinkingMeasurement()
