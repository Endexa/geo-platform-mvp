"""BV-012: Influencer Mentions"""

from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger
from geo_data_points.measurements.base_measurement import BaseMeasurement


class InfluencerMentionsMeasurement(BaseMeasurement):
    """Measures mentions by industry influencers."""

    async def measure(self, url: str, html: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start = datetime.utcnow()

        try:
            influencer_mentions = metadata.get('influencer_mentions', 0) if metadata else 0

            if influencer_mentions >= 50:
                score = 100
            elif influencer_mentions >= 20:
                score = 85
            elif influencer_mentions >= 10:
                score = 70
            elif influencer_mentions >= 1:
                score = 50
            else:
                score = 30

            return {
                'score': score,
                'comment': f"{influencer_mentions} influencer mentions",
                'metadata': {
                    'measurement_id': 'BV-012',
                    'influencer_mentions': influencer_mentions,
                    'execution_time_ms': int((datetime.utcnow() - start).total_seconds() * 1000)
                },
                'recommendations': ['Build influencer relationships'] if influencer_mentions < 10 else []
            }

        except Exception as e:
            logger.error(f"[BV-012] Error: {e}")
            return {'score': 0, 'comment': f"Error: {e}", 'metadata': {'measurement_id': 'BV-012'}, 'recommendations': []}
