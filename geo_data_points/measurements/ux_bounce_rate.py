"""UX-005: Bounce Rate"""

from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger
from geo_data_points.measurements.base_measurement import BaseMeasurement


class BounceRateMeasurement(BaseMeasurement):
    """Measures bounce rate (requires analytics data)."""

    async def measure(self, url: str, html: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start = datetime.utcnow()

        try:
            # Get bounce rate from metadata (Google Analytics typically)
            bounce_rate = metadata.get('bounce_rate', 50) if metadata else 50

            # Lower bounce rate = better score
            if bounce_rate < 20:
                score = 100
            elif bounce_rate < 30:
                score = 90
            elif bounce_rate < 40:
                score = 80
            elif bounce_rate < 50:
                score = 70
            elif bounce_rate < 60:
                score = 60
            elif bounce_rate < 70:
                score = 40
            else:
                score = 20

            return {
                'score': score,
                'comment': f"Bounce rate: {bounce_rate:.1f}%",
                'metadata': {
                    'measurement_id': 'UX-005',
                    'bounce_rate': bounce_rate,
                    'execution_time_ms': int((datetime.utcnow() - start).total_seconds() * 1000)
                },
                'recommendations': ['Improve content engagement to reduce bounce rate'] if bounce_rate > 50 else []
            }

        except Exception as e:
            logger.error(f"[UX-005] Error: {e}")
            return {'score': 0, 'comment': f"Error: {e}", 'metadata': {'measurement_id': 'UX-005'}, 'recommendations': []}
