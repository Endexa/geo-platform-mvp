"""
Response Time Check

Measures server response time for the URL.
Fast response times improve user experience and crawler efficiency.

Module: WI (Web Infrastructure)
Priority: High
Automation: Full
"""

import time
from typing import Dict, Any
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from scripts.base_measurement import BaseMeasurement
from utils import fetch_url, calculate_percentage_score


class ResponseTime(BaseMeasurement):
    """
    Measure server response time.

    Score:
    - 100: < 200ms (Excellent)
    - 75-99: 200-500ms (Good)
    - 50-74: 500-1000ms (Average)
    - 25-49: 1000-2000ms (Slow)
    - 0-24: > 2000ms (Very slow)
    """

    def measure(self) -> Dict[str, Any]:
        """
        Measure response time of the URL.

        Returns:
            dict: Score and comment about response time
        """
        start_time = time.time()
        response = fetch_url(self.url)
        elapsed_ms = (time.time() - start_time) * 1000

        if not response:
            return self._default_error_result("Failed to fetch URL")

        # Calculate score (inverted: lower time = higher score)
        # Excellent: < 200ms → 100
        # Good: 200-500ms → 75-99
        # Average: 500-1000ms → 50-74
        # Slow: 1000-2000ms → 25-49
        # Very slow: > 2000ms → 0-24

        if elapsed_ms < 200:
            score = 100.0
            rating = "Excellent"
        elif elapsed_ms < 500:
            score = calculate_percentage_score(elapsed_ms, 200, 500, invert=True)
            score = 75 + (score / 100 * 25)  # Scale to 75-100 range
            rating = "Good"
        elif elapsed_ms < 1000:
            score = calculate_percentage_score(elapsed_ms, 500, 1000, invert=True)
            score = 50 + (score / 100 * 25)  # Scale to 50-75 range
            rating = "Average"
        elif elapsed_ms < 2000:
            score = calculate_percentage_score(elapsed_ms, 1000, 2000, invert=True)
            score = 25 + (score / 100 * 25)  # Scale to 25-50 range
            rating = "Slow"
        else:
            score = min(25, calculate_percentage_score(elapsed_ms, 2000, 5000, invert=True))
            rating = "Very Slow"

        # Generate comment
        comment = f'Response time: {elapsed_ms:.0f}ms ({rating}). '

        if elapsed_ms < 200:
            comment += '✓ Excellent for GEO - fast crawling and indexing.'
        elif elapsed_ms < 500:
            comment += '✓ Good response time. Consider further optimization.'
        elif elapsed_ms < 1000:
            comment += '⚠ Average response time. Optimize to improve crawler efficiency.'
        elif elapsed_ms < 2000:
            comment += '✗ Slow response time. Significant optimization needed.'
        else:
            comment += '✗ Very slow response time. Critical performance issue.'

        return {
            'score': round(score, 2),
            'comment': comment,
            'metadata': {
                'response_time_ms': round(elapsed_ms, 2),
                'rating': rating,
                'status_code': response.status_code,
                'recommendation': 'Target < 200ms for optimal GEO performance.' if elapsed_ms >= 200 else None
            }
        }


if __name__ == "__main__":
    import sys
    test_url = sys.argv[1] if len(sys.argv) > 1 else "https://anthropic.com"

    measurement = ResponseTime(test_url)
    result = measurement.run()
    print(f"Score: {result['score']}")
    print(f"Comment: {result['comment']}")
    print(f"Response Time: {result['metadata']['response_time_ms']}ms")
