"""COMP-004: Market Position"""

from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger
from geo_data_points.measurements.base_measurement import BaseMeasurement


class MarketPositionMeasurement(BaseMeasurement):
    """Measures market position relative to competitors."""

    async def measure(self, url: str, html: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start = datetime.utcnow()

        try:
            # Get market metrics from metadata
            market_rank = metadata.get('market_rank', 50) if metadata else 50
            total_competitors = metadata.get('total_competitors', 100) if metadata else 100

            # Calculate position percentage (higher is better)
            position_pct = ((total_competitors - market_rank) / total_competitors) * 100

            # Score
            if market_rank <= 3:
                score = 100
            elif market_rank <= 10:
                score = 85
            elif market_rank <= 25:
                score = 70
            elif market_rank <= 50:
                score = 50
            else:
                score = 30

            return {
                'score': score,
                'comment': f"Market rank: #{market_rank} out of {total_competitors} competitors",
                'metadata': {
                    'measurement_id': 'COMP-004',
                    'market_rank': market_rank,
                    'total_competitors': total_competitors,
                    'position_pct': position_pct,
                    'execution_time_ms': int((datetime.utcnow() - start).total_seconds() * 1000)
                },
                'recommendations': ['Improve competitive positioning through differentiation'] if market_rank > 25 else []
            }

        except Exception as e:
            logger.error(f"[COMP-004] Error: {e}")
            return {'score': 0, 'comment': f"Error: {e}", 'metadata': {'measurement_id': 'COMP-004'}, 'recommendations': []}
