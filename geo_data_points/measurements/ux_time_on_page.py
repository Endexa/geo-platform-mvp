"""UX-006: Time on Page"""

from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger
from geo_data_points.measurements.base_measurement import BaseMeasurement


class TimeOnPageMeasurement(BaseMeasurement):
    """Measures average time users spend on page."""

    async def measure(self, url: str, html: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start = datetime.utcnow()

        try:
            # Get time on page from metadata (seconds)
            time_on_page = metadata.get('avg_time_on_page', 30) if metadata else 30

            # Score based on engagement time
            if time_on_page >= 180:  # 3+ minutes
                score = 100
            elif time_on_page >= 120:  # 2+ minutes
                score = 85
            elif time_on_page >= 60:  # 1+ minute
                score = 70
            elif time_on_page >= 30:  # 30+ seconds
                score = 50
            else:
                score = 20

            return {
                'score': score,
                'comment': f"Average time on page: {time_on_page:.0f} seconds",
                'metadata': {
                    'measurement_id': 'UX-006',
                    'time_on_page_seconds': time_on_page,
                    'execution_time_ms': int((datetime.utcnow() - start).total_seconds() * 1000)
                },
                'recommendations': ['Improve content engagement to increase time on page'] if time_on_page < 60 else []
            }

        except Exception as e:
            logger.error(f"[UX-006] Error: {e}")
            return {'score': 0, 'comment': f"Error: {e}", 'metadata': {'measurement_id': 'UX-006'}, 'recommendations': []}
