"""CNT-013: List Usage - Measures use of lists for scannable content"""

from typing import Dict, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from loguru import logger
from geo_data_points.measurements.base_measurement import BaseMeasurement


class ListUsageMeasurement(BaseMeasurement):
    """Measures use of ordered and unordered lists."""

    async def measure(self, url: str, html: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start = datetime.utcnow()

        try:
            soup = BeautifulSoup(html, 'lxml')

            # Count lists
            ul_count = len(soup.find_all('ul'))
            ol_count = len(soup.find_all('ol'))
            total_lists = ul_count + ol_count

            # Count list items
            li_count = len(soup.find_all('li'))

            # Score based on list usage
            if total_lists >= 5 and li_count >= 20:
                score = 100
            elif total_lists >= 3 and li_count >= 10:
                score = 80
            elif total_lists >= 2 and li_count >= 5:
                score = 60
            elif total_lists >= 1:
                score = 40
            else:
                score = 0

            return {
                'score': score,
                'comment': f"{total_lists} lists with {li_count} items total",
                'metadata': {
                    'measurement_id': 'CNT-013',
                    'ul_count': ul_count,
                    'ol_count': ol_count,
                    'li_count': li_count,
                    'execution_time_ms': int((datetime.utcnow() - start).total_seconds() * 1000)
                },
                'recommendations': ['Add more lists for better scannability'] if total_lists < 3 else []
            }

        except Exception as e:
            logger.error(f"[CNT-013] Error: {e}")
            return {'score': 0, 'comment': f"Error: {e}", 'metadata': {'measurement_id': 'CNT-013'}, 'recommendations': []}
