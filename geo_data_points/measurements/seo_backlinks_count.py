"""
SEO-001: Backlinks Count

Measures the number of backlinks pointing to the domain.
Backlinks are a strong authority signal for AI models.
"""

from typing import Dict, Any
from geo_data_points.base import BaseMeasurement
from geo_data_points.utils.external_apis import CommonCrawlClient
from loguru import logger


class BacklinksCountMeasurement(BaseMeasurement):
    """Measure backlinks count from external sources."""

    def __init__(self):
        super().__init__(
            code="SEO-001",
            name="Backlinks Count",
            description="Measures number of backlinks pointing to domain",
            category="SEO",
            weight=0.90  # Very high importance for authority
        )
        self.cc_client = CommonCrawlClient()

    async def measure(self, url: str, html: str = None, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Measure backlinks count.

        Scoring:
        - 100: 1000+ backlinks (high authority)
        - 90: 500-1000 backlinks
        - 80: 100-500 backlinks
        - 70: 50-100 backlinks
        - 60: 20-50 backlinks
        - 40: 5-20 backlinks
        - 20: 1-5 backlinks
        - 0: No backlinks found

        Args:
            url: Target URL to analyze
            html: Unused
            metadata: Unused

        Returns:
            Dict with score (0-100) and detailed comment
        """
        try:
            # Extract domain from URL
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.replace('www.', '')

            # Get backlinks count from Common Crawl
            backlinks_data = self.cc_client.get_backlinks_count(domain)

            if not backlinks_data or 'error' in backlinks_data:
                # Fallback: estimate from simple heuristics
                return {
                    'score': 0,
                    'comment': f'Cannot measure backlinks for {domain}. API unavailable or domain not indexed. Backlinks are critical for AI model authority signals. Build quality backlinks from authoritative sites.'
                }

            backlinks_count = backlinks_data.get('count', 0)

            if backlinks_count == 0:
                return {
                    'score': 0,
                    'comment': f'No backlinks found for {domain}. Critical issue! AI models heavily weight backlinks for authority. Start link building: guest posts, partnerships, quality content that earns links.'
                }

            # Determine score based on backlinks count
            if backlinks_count >= 1000:
                score = 100
                authority = "Very High Authority"
                comment = f'{authority}: {backlinks_count:,} backlinks found. Excellent domain authority for AI model citation preference!'
            elif backlinks_count >= 500:
                score = 90
                authority = "High Authority"
                comment = f'{authority}: {backlinks_count:,} backlinks found. Strong authority signals for AI models.'
            elif backlinks_count >= 100:
                score = 80
                authority = "Good Authority"
                comment = f'{authority}: {backlinks_count:,} backlinks found. Solid foundation - continue building quality backlinks.'
            elif backlinks_count >= 50:
                score = 70
                authority = "Moderate Authority"
                comment = f'{authority}: {backlinks_count:,} backlinks found. Growing authority - focus on quality backlinks from high-DR sites.'
            elif backlinks_count >= 20:
                score = 60
                authority = "Emerging Authority"
                comment = f'{authority}: {backlinks_count:,} backlinks found. Early stage - accelerate link building efforts.'
            elif backlinks_count >= 5:
                score = 40
                authority = "Low Authority"
                comment = f'{authority}: Only {backlinks_count} backlinks found. Critical: AI models may skip low-authority sites. Priority: build backlinks from authoritative domains.'
            else:
                score = 20
                authority = "Very Low Authority"
                comment = f'{authority}: Only {backlinks_count} backlinks found. Severely limited authority. Urgent action needed: guest posting, partnerships, PR, quality content.'

            # Add referring domains info if available
            if 'referring_domains' in backlinks_data:
                ref_domains = backlinks_data['referring_domains']
                comment += f' Referring domains: {ref_domains:,}.'

                # Bonus for domain diversity
                if ref_domains >= backlinks_count * 0.3:  # Good domain diversity
                    score = min(100, score + 5)
                    comment += ' Good domain diversity (quality signal).'

            # Recommendations
            if backlinks_count < 100:
                comment += ' Tip: Create link-worthy content, reach out for guest posts, build relationships with industry sites.'

            return {
                'score': score,
                'comment': comment
            }

        except Exception as e:
            logger.error(f"Error measuring backlinks for {url}: {str(e)}")
            return {
                'score': 0,
                'comment': f'Measurement failed: {str(e)}'
            }


# Export for orchestrator
measurement = BacklinksCountMeasurement()
