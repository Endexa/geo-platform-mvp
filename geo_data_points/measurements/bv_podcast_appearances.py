"""BV-010: Podcast Appearances"""

from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger
from geo_data_points.measurements.base_measurement import BaseMeasurement


class PodcastAppearancesMeasurement(BaseMeasurement):
    """Measures podcast appearances and mentions."""

    async def measure(self, url: str, html: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start = datetime.utcnow()

        try:
            podcast_count = metadata.get('podcast_appearances', 0) if metadata else 0

            if podcast_count >= 20:
                score = 100
            elif podcast_count >= 10:
                score = 85
            elif podcast_count >= 5:
                score = 70
            elif podcast_count >= 1:
                score = 50
            else:
                score = 30

            return {
                'score': score,
                'comment': f"{podcast_count} podcast appearances",
                'metadata': {
                    'measurement_id': 'BV-010',
                    'podcast_count': podcast_count,
                    'execution_time_ms': int((datetime.utcnow() - start).total_seconds() * 1000)
                },
                'recommendations': ['Develop podcast outreach strategy'] if podcast_count < 5 else []
            }

        except Exception as e:
            logger.error(f"[BV-010] Error: {e}")
            return {'score': 0, 'comment': f"Error: {e}", 'metadata': {'measurement_id': 'BV-010'}, 'recommendations': []}
