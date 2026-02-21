"""BV-006: Press Coverage"""

from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger
from geo_data_points.measurements.base_measurement import BaseMeasurement


class PressCoverageMeasurement(BaseMeasurement):
    """Measures press mentions and media coverage."""

    async def measure(self, url: str, html: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start = datetime.utcnow()

        try:
            # Get press metrics from metadata
            press_mentions = metadata.get('press_mentions', 0) if metadata else 0
            high_authority_mentions = metadata.get('high_authority_press', 0) if metadata else 0

            # Score
            if press_mentions >= 50 and high_authority_mentions >= 10:
                score = 100
            elif press_mentions >= 20 and high_authority_mentions >= 5:
                score = 85
            elif press_mentions >= 10 and high_authority_mentions >= 2:
                score = 70
            elif press_mentions >= 5:
                score = 50
            elif press_mentions >= 1:
                score = 30
            else:
                score = 0

            return {
                'score': score,
                'comment': f"{press_mentions} press mentions ({high_authority_mentions} from major outlets)",
                'metadata': {
                    'measurement_id': 'BV-006',
                    'press_mentions': press_mentions,
                    'high_authority_mentions': high_authority_mentions,
                    'execution_time_ms': int((datetime.utcnow() - start).total_seconds() * 1000)
                },
                'recommendations': ['Develop PR strategy to increase press coverage'] if press_mentions < 10 else []
            }

        except Exception as e:
            logger.error(f"[BV-006] Error: {e}")
            return {'score': 0, 'comment': f"Error: {e}", 'metadata': {'measurement_id': 'BV-006'}, 'recommendations': []}
