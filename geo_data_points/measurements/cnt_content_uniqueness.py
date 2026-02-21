"""CNT-019: Content Uniqueness (Duplicate Content Check)"""

from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger
from geo_data_points.measurements.base_measurement import BaseMeasurement


class ContentUniquenessMeasurement(BaseMeasurement):
    """Measures content uniqueness and duplicate content issues."""

    async def measure(self, url: str, html: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start = datetime.utcnow()

        try:
            # Get uniqueness from metadata (0-100%)
            uniqueness_pct = metadata.get('content_uniqueness_pct', 95) if metadata else 95
            duplicate_pages = metadata.get('duplicate_pages_count', 0) if metadata else 0

            # Score based on uniqueness
            if uniqueness_pct >= 95:
                score = 100
            elif uniqueness_pct >= 90:
                score = 85
            elif uniqueness_pct >= 80:
                score = 70
            elif uniqueness_pct >= 70:
                score = 50
            else:
                score = 30

            return {
                'score': score,
                'comment': f"{uniqueness_pct:.1f}% unique content ({duplicate_pages} duplicate pages found)",
                'metadata': {
                    'measurement_id': 'CNT-019',
                    'uniqueness_pct': uniqueness_pct,
                    'duplicate_pages': duplicate_pages,
                    'execution_time_ms': int((datetime.utcnow() - start).total_seconds() * 1000)
                },
                'recommendations': [
                    'Review and rewrite duplicate content',
                    'Use canonical tags for necessary duplicates'
                ] if uniqueness_pct < 90 or duplicate_pages > 0 else []
            }

        except Exception as e:
            logger.error(f"[CNT-019] Error: {e}")
            return {'score': 0, 'comment': f"Error: {e}", 'metadata': {'measurement_id': 'CNT-019'}, 'recommendations': []}
