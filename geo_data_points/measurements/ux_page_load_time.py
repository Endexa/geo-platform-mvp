"""
UX-002: Page Load Time (TTFB - Time To First Byte)

Measures server response time (TTFB) for page delivery.
Fast TTFB is critical for both user experience and AI crawler efficiency.
"""

from typing import Dict, Any
from geo_data_points.base import BaseMeasurement
from geo_data_points.utils.http_client import CachedSession
from loguru import logger
import time


class PageLoadTimeMeasurement(BaseMeasurement):
    """Measure page load time (TTFB)."""

    def __init__(self):
        super().__init__(
            code="UX-002",
            name="Page Load Time (TTFB)",
            description="Measures Time To First Byte (TTFB) for server response speed",
            category="User Experience",
            weight=0.90  # Critical for performance and crawler efficiency
        )
        self.session = CachedSession()

    async def measure(self, url: str, html: str = None, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Measure TTFB performance.

        Scoring (Google's recommended thresholds):
        - 100: TTFB ≤ 200ms (Excellent)
        - 90: TTFB 200-400ms (Good)
        - 75: TTFB 400-600ms (Acceptable)
        - 60: TTFB 600-800ms (Slow)
        - 40: TTFB 800-1000ms (Very Slow)
        - 20: TTFB > 1000ms (Critical)
        - 0: Cannot measure

        Args:
            url: Target URL to analyze
            html: Unused (measures network response)
            metadata: Unused

        Returns:
            Dict with score (0-100) and detailed comment
        """
        try:
            # Perform multiple measurements for accuracy
            num_tests = 3
            ttfb_measurements = []

            for i in range(num_tests):
                try:
                    start_time = time.time()

                    # Make request (don't use cache for accurate measurement)
                    response = self.session.session.get(
                        url,
                        timeout=10,
                        allow_redirects=True,
                        stream=True
                    )

                    # Calculate TTFB (time until first byte received)
                    ttfb = (time.time() - start_time) * 1000  # Convert to milliseconds

                    ttfb_measurements.append(ttfb)

                    # Close connection
                    response.close()

                    # Small delay between tests
                    if i < num_tests - 1:
                        time.sleep(0.5)

                except Exception as e:
                    logger.warning(f"TTFB measurement {i+1} failed: {str(e)}")
                    continue

            if not ttfb_measurements:
                return {
                    'score': 0,
                    'comment': f'Cannot measure TTFB for {url}. Ensure URL is accessible and server is responding.'
                }

            # Calculate statistics
            avg_ttfb = sum(ttfb_measurements) / len(ttfb_measurements)
            min_ttfb = min(ttfb_measurements)
            max_ttfb = max(ttfb_measurements)

            # Calculate standard deviation for consistency check
            if len(ttfb_measurements) > 1:
                variance = sum((x - avg_ttfb) ** 2 for x in ttfb_measurements) / len(ttfb_measurements)
                std_dev = variance ** 0.5
            else:
                std_dev = 0

            # ========== SCORING BASED ON AVERAGE TTFB ==========
            if avg_ttfb <= 200:
                score = 100
                performance = "Excellent"
                comment = f'{performance} TTFB: {avg_ttfb:.0f}ms (≤200ms). Outstanding server response! Perfect for AI crawler efficiency and user experience.'
            elif avg_ttfb <= 400:
                score = 90
                performance = "Good"
                comment = f'{performance} TTFB: {avg_ttfb:.0f}ms (200-400ms). Fast server response. Great for AI crawlers and users.'
            elif avg_ttfb <= 600:
                score = 75
                performance = "Acceptable"
                comment = f'{performance} TTFB: {avg_ttfb:.0f}ms (400-600ms). Reasonable response time. Consider optimization for better AI crawler efficiency.'
            elif avg_ttfb <= 800:
                score = 60
                performance = "Slow"
                comment = f'{performance} TTFB: {avg_ttfb:.0f}ms (600-800ms). Slow server response. Optimization needed - may affect AI crawler behavior.'
            elif avg_ttfb <= 1000:
                score = 40
                performance = "Very Slow"
                comment = f'{performance} TTFB: {avg_ttfb:.0f}ms (800-1000ms). Very slow server. Critical optimization needed - AI crawlers may deprioritize slow sites.'
            else:
                score = 20
                performance = "Critical"
                comment = f'{performance} TTFB: {avg_ttfb:.0f}ms (>1000ms). Extremely slow server response! Urgent action required - AI crawlers will significantly deprioritize or skip slow sites.'

            # Add measurement details
            comment += f' Measurements: min={min_ttfb:.0f}ms, avg={avg_ttfb:.0f}ms, max={max_ttfb:.0f}ms.'

            # Check consistency
            if std_dev > avg_ttfb * 0.3:  # High variance (>30% of average)
                comment += f' High variance ({std_dev:.0f}ms std dev) - inconsistent performance detected.'
                score = max(0, score - 10)

            # ========== OPTIMIZATION RECOMMENDATIONS ==========
            recommendations = []

            if avg_ttfb > 400:
                if avg_ttfb > 800:
                    recommendations.append('URGENT: Optimize server configuration')
                    recommendations.append('Use CDN for global distribution')
                    recommendations.append('Enable HTTP/2 or HTTP/3')
                    recommendations.append('Implement server-side caching')
                    recommendations.append('Upgrade server resources (CPU/RAM)')
                else:
                    recommendations.append('Enable HTTP/2')
                    recommendations.append('Optimize database queries')
                    recommendations.append('Implement caching (Redis/Memcached)')
                    recommendations.append('Use CDN for static assets')

            if recommendations:
                comment += f' Optimization tips: {"; ".join(recommendations[:3])}.'

            # ========== PERFORMANCE CONTEXT ==========
            if avg_ttfb <= 200:
                comment += ' AI crawlers will prioritize your fast site.'
            elif avg_ttfb <= 600:
                comment += ' Acceptable for AI crawler access.'
            else:
                comment += ' Slow TTFB may reduce AI crawler frequency and priority.'

            # Check if redirects affected TTFB
            try:
                response = self.session.session.head(url, allow_redirects=False, timeout=5)
                if response.status_code in [301, 302, 303, 307, 308]:
                    comment += ' Note: Redirects detected - may increase TTFB. Minimize redirect chains.'
            except:
                pass

            return {
                'score': score,
                'comment': comment,
                'raw_value': avg_ttfb,
                'metadata': {
                    'ttfb_ms': avg_ttfb,
                    'min_ttfb_ms': min_ttfb,
                    'max_ttfb_ms': max_ttfb,
                    'std_dev_ms': std_dev,
                    'num_measurements': len(ttfb_measurements)
                }
            }

        except Exception as e:
            logger.error(f"Error measuring TTFB for {url}: {str(e)}")
            return {
                'score': 0,
                'comment': f'TTFB measurement failed: {str(e)}. Ensure server is accessible.'
            }


# Export for orchestrator
measurement = PageLoadTimeMeasurement()
