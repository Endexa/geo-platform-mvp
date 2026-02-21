"""WI-026: Lazy Loading Implementation"""

from typing import Dict, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from loguru import logger
from geo_data_points.measurements.base_measurement import BaseMeasurement


class LazyLoadingMeasurement(BaseMeasurement):
    """Measures lazy loading implementation for images and iframes."""

    async def measure(self, url: str, html: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start = datetime.utcnow()

        try:
            soup = BeautifulSoup(html, 'lxml')

            images = soup.find_all('img')
            iframes = soup.find_all('iframe')
            total_media = len(images) + len(iframes)

            if total_media == 0:
                return {
                    'score': 100,
                    'comment': "No images or iframes found",
                    'metadata': {'measurement_id': 'WI-026'},
                    'recommendations': []
                }

            lazy_images = sum(1 for img in images if img.get('loading') == 'lazy')
            lazy_iframes = sum(1 for iframe in iframes if iframe.get('loading') == 'lazy')
            total_lazy = lazy_images + lazy_iframes

            lazy_percentage = (total_lazy / total_media) * 100
            score = int(lazy_percentage)

            return {
                'score': score,
                'comment': f"{total_lazy}/{total_media} elements use lazy loading ({lazy_percentage:.1f}%)",
                'metadata': {
                    'measurement_id': 'WI-026',
                    'total_media': total_media,
                    'lazy_loaded': total_lazy,
                    'lazy_percentage': lazy_percentage,
                    'execution_time_ms': int((datetime.utcnow() - start).total_seconds() * 1000)
                },
                'recommendations': ['Implement lazy loading for images and iframes'] if score < 80 else []
            }

        except Exception as e:
            logger.error(f"[WI-026] Error: {e}")
            return {'score': 0, 'comment': f"Error: {e}", 'metadata': {'measurement_id': 'WI-026'}, 'recommendations': []}
