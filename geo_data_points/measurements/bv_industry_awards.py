"""BV-009: Industry Awards & Recognition"""

from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger
from geo_data_points.measurements.base_measurement import BaseMeasurement


class IndustryAwardsMeasurement(BaseMeasurement):
    """Measures industry awards and recognition."""

    async def measure(self, url: str, html: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start = datetime.utcnow()

        try:
            awards_count = metadata.get('awards_count', 0) if metadata else 0

            # Score
            if awards_count >= 10:
                score = 100
            elif awards_count >= 5:
                score = 85
            elif awards_count >= 3:
                score = 70
            elif awards_count >= 1:
                score = 50
            else:
                score = 30

            return {
                'score': score,
                'comment': f"{awards_count} industry awards/recognition",
                'metadata': {
                    'measurement_id': 'BV-009',
                    'awards_count': awards_count,
                    'execution_time_ms': int((datetime.utcnow() - start).total_seconds() * 1000)
                },
                'recommendations': ['Document awards and recognition on website'] if awards_count < 3 else []
            }

        except Exception as e:
            logger.error(f"[BV-009] Error: {e}")
            return {'score': 0, 'comment': f"Error: {e}", 'metadata': {'measurement_id': 'BV-009'}, 'recommendations': []}
