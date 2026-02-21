"""BV-015: Community Involvement"""

from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger
from geo_data_points.measurements.base_measurement import BaseMeasurement


class CommunityInvolvementMeasurement(BaseMeasurement):
    async def measure(self, url: str, html: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start = datetime.utcnow()
        try:
            community_score = metadata.get('community_involvement_score', 50) if metadata else 50
            return {
                'score': int(community_score),
                'comment': f"Community involvement: {community_score}/100",
                'metadata': {'measurement_id': 'BV-015', 'community_score': community_score, 'execution_time_ms': int((datetime.utcnow() - start).total_seconds() * 1000)},
                'recommendations': ['Increase community engagement activities'] if community_score < 60 else []
            }
        except Exception as e:
            logger.error(f"[BV-015] Error: {e}")
            return {'score': 0, 'comment': f"Error: {e}", 'metadata': {'measurement_id': 'BV-015'}, 'recommendations': []}
