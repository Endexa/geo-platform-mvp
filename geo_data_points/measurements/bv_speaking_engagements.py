"""BV-014: Speaking Engagements"""

from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger
from geo_data_points.measurements.base_measurement import BaseMeasurement


class SpeakingEngagementsMeasurement(BaseMeasurement):
    async def measure(self, url: str, html: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start = datetime.utcnow()
        try:
            speaking_events = metadata.get('speaking_events', 0) if metadata else 0
            score = min(100, speaking_events * 5)
            return {
                'score': score,
                'comment': f"{speaking_events} speaking engagements",
                'metadata': {'measurement_id': 'BV-014', 'speaking_events': speaking_events, 'execution_time_ms': int((datetime.utcnow() - start).total_seconds() * 1000)},
                'recommendations': ['Pursue speaking opportunities'] if speaking_events < 10 else []
            }
        except Exception as e:
            logger.error(f"[BV-014] Error: {e}")
            return {'score': 0, 'comment': f"Error: {e}", 'metadata': {'measurement_id': 'BV-014'}, 'recommendations': []}
