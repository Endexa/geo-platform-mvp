"""BV-008: Brand Sentiment"""

from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger
from geo_data_points.measurements.base_measurement import BaseMeasurement


class BrandSentimentMeasurement(BaseMeasurement):
    """Measures brand sentiment from online mentions."""

    async def measure(self, url: str, html: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start = datetime.utcnow()

        try:
            # Get sentiment from metadata (scale: -1 to +1)
            sentiment_score = metadata.get('sentiment_score', 0) if metadata else 0
            positive_pct = metadata.get('positive_mentions_pct', 50) if metadata else 50
            negative_pct = metadata.get('negative_mentions_pct', 10) if metadata else 10

            # Convert to 0-100 scale
            score = int(((sentiment_score + 1) / 2) * 100)

            if sentiment_score >= 0.5:
                label = "Very Positive"
            elif sentiment_score >= 0.2:
                label = "Positive"
            elif sentiment_score >= -0.2:
                label = "Neutral"
            elif sentiment_score >= -0.5:
                label = "Negative"
            else:
                label = "Very Negative"

            return {
                'score': score,
                'comment': f"Brand sentiment: {label} ({positive_pct:.0f}% positive, {negative_pct:.0f}% negative)",
                'metadata': {
                    'measurement_id': 'BV-008',
                    'sentiment_score': sentiment_score,
                    'positive_pct': positive_pct,
                    'negative_pct': negative_pct,
                    'label': label,
                    'execution_time_ms': int((datetime.utcnow() - start).total_seconds() * 1000)
                },
                'recommendations': [
                    'Monitor and respond to negative mentions',
                    'Implement reputation management strategy'
                ] if sentiment_score < 0 else []
            }

        except Exception as e:
            logger.error(f"[BV-008] Error: {e}")
            return {'score': 0, 'comment': f"Error: {e}", 'metadata': {'measurement_id': 'BV-008'}, 'recommendations': []}
