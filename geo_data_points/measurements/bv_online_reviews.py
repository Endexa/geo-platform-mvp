"""BV-007: Online Reviews"""

from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger
from geo_data_points.measurements.base_measurement import BaseMeasurement


class OnlineReviewsMeasurement(BaseMeasurement):
    """Measures quantity and quality of online reviews."""

    async def measure(self, url: str, html: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start = datetime.utcnow()

        try:
            # Get review metrics from metadata
            review_count = metadata.get('review_count', 0) if metadata else 0
            avg_rating = metadata.get('avg_rating', 0) if metadata else 0

            # Score based on both quantity and quality
            quantity_score = min(100, (review_count / 100) * 100)  # Up to 100 reviews
            quality_score = (avg_rating / 5) * 100  # Out of 5 stars

            score = int((quantity_score * 0.4) + (quality_score * 0.6))

            return {
                'score': score,
                'comment': f"{review_count} reviews with {avg_rating:.1f}/5.0 average rating",
                'metadata': {
                    'measurement_id': 'BV-007',
                    'review_count': review_count,
                    'avg_rating': avg_rating,
                    'execution_time_ms': int((datetime.utcnow() - start).total_seconds() * 1000)
                },
                'recommendations': [
                    'Encourage customers to leave reviews',
                    'Respond to reviews to improve engagement'
                ] if review_count < 20 or avg_rating < 4.0 else []
            }

        except Exception as e:
            logger.error(f"[BV-007] Error: {e}")
            return {'score': 0, 'comment': f"Error: {e}", 'metadata': {'measurement_id': 'BV-007'}, 'recommendations': []}
