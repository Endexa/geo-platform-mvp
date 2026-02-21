"""WI-031: Resource Preloading"""

from typing import Dict, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from loguru import logger
from geo_data_points.measurements.base_measurement import BaseMeasurement


class PreloadResourcesMeasurement(BaseMeasurement):
    """Measures resource preloading implementation."""

    async def measure(self, url: str, html: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start = datetime.utcnow()

        try:
            soup = BeautifulSoup(html, 'lxml')

            # Find preload tags
            preload_links = soup.find_all('link', rel='preload')

            # Score
            if len(preload_links) >= 5:
                score = 100
            elif len(preload_links) >= 3:
                score = 85
            elif len(preload_links) >= 1:
                score = 70
            else:
                score = 50  # Not critical

            return {
                'score': score,
                'comment': f"{len(preload_links)} resources preloaded",
                'metadata': {
                    'measurement_id': 'WI-031',
                    'preload_count': len(preload_links),
                    'execution_time_ms': int((datetime.utcnow() - start).total_seconds() * 1000)
                },
                'recommendations': ['Preload critical resources (fonts, CSS, JS)'] if len(preload_links) < 3 else []
            }

        except Exception as e:
            logger.error(f"[WI-031] Error: {e}")
            return {'score': 0, 'comment': f"Error: {e}", 'metadata': {'measurement_id': 'WI-031'}, 'recommendations': []}
