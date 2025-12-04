"""
UX-001: Core Web Vitals - LCP (Largest Contentful Paint)

Measures Largest Contentful Paint using PageSpeed Insights API.
LCP is critical for user experience and AI crawler efficiency.
"""

from typing import Dict, Any
from geo_data_points.base import BaseMeasurement
from geo_data_points.utils.external_apis import PageSpeedClient
from loguru import logger


class CoreWebVitalsLCPMeasurement(BaseMeasurement):
    """Measure LCP (Largest Contentful Paint) performance."""

    def __init__(self):
        super().__init__(
            code="UX-001",
            name="Core Web Vitals - LCP",
            description="Measures Largest Contentful Paint (LCP) for page loading performance",
            category="User Experience",
            weight=0.95  # Critical for UX and crawler efficiency
        )
        self.pagespeed_client = PageSpeedClient()

    async def measure(self, url: str, html: str = None, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Measure LCP performance.

        Scoring (based on Google's Core Web Vitals thresholds):
        - 100: LCP ≤ 2.5s (Good)
        - 70: LCP 2.5-4.0s (Needs Improvement)
        - 30: LCP > 4.0s (Poor)
        - 0: Cannot measure or API error

        Args:
            url: Target URL to analyze
            html: Unused (measurement via API)
            metadata: Unused

        Returns:
            Dict with score (0-100) and detailed comment
        """
        try:
            # Get Core Web Vitals from PageSpeed Insights
            vitals = self.pagespeed_client.get_core_web_vitals(url)

            if not vitals or 'error' in vitals:
                error_msg = vitals.get('error', 'Unknown error') if vitals else 'API unavailable'
                return {
                    'score': 0,
                    'comment': f'Cannot measure LCP: {error_msg}. Ensure PageSpeed Insights API is configured and URL is accessible.'
                }

            lcp = vitals.get('lcp')

            if lcp is None:
                return {
                    'score': 0,
                    'comment': 'LCP data not available from PageSpeed Insights. URL may not be publicly accessible or have insufficient traffic data.'
                }

            # LCP is in seconds
            # Thresholds: Good ≤ 2.5s, Needs Improvement 2.5-4.0s, Poor > 4.0s

            if lcp <= 2.5:
                score = 100
                rating = "Good"
                comment = f'Excellent LCP: {lcp:.2f}s (Good - ≤ 2.5s). Fast content loading enhances AI crawler efficiency and user experience!'
            elif lcp <= 4.0:
                score = 70
                rating = "Needs Improvement"
                comment = f'Moderate LCP: {lcp:.2f}s (Needs Improvement - 2.5-4.0s). Optimize to <2.5s for better performance. AI crawlers may deprioritize slow sites.'
            else:
                score = 30
                rating = "Poor"
                comment = f'Poor LCP: {lcp:.2f}s (Poor - >4.0s). Critical optimization needed! Slow loading severely impacts AI crawler efficiency and user experience.'

            # Add optimization tips based on LCP value
            if lcp > 2.5:
                tips = []
                if lcp > 4.0:
                    tips.append('Optimize server response time (TTFB)')
                    tips.append('Use CDN for static assets')
                tips.append('Optimize images (WebP, lazy loading)')
                tips.append('Eliminate render-blocking resources')
                tips.append('Implement resource hints (preload, preconnect)')

                comment += f' Optimization tips: {"; ".join(tips[:3])}.'

            # Add PageSpeed score if available
            if 'performance_score' in vitals:
                perf_score = vitals['performance_score']
                comment += f' Overall PageSpeed score: {perf_score}/100.'

            return {
                'score': score,
                'comment': comment
            }

        except Exception as e:
            logger.error(f"Error measuring LCP for {url}: {str(e)}")
            return {
                'score': 0,
                'comment': f'Measurement failed: {str(e)}'
            }


# Export for orchestrator
measurement = CoreWebVitalsLCPMeasurement()
