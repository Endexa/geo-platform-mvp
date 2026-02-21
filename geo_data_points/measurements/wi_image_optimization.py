"""WI-023: Image Optimization"""

from typing import Dict, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from loguru import logger
from geo_data_points.measurements.base_measurement import BaseMeasurement


class ImageOptimizationMeasurement(BaseMeasurement):
    """Measures image optimization (modern formats, lazy loading, dimensions)."""

    async def measure(self, url: str, html: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start = datetime.utcnow()

        try:
            soup = BeautifulSoup(html, 'lxml')
            images = soup.find_all('img')

            if not images:
                return {
                    'score': 100,
                    'comment': "No images found",
                    'metadata': {'measurement_id': 'WI-023'},
                    'recommendations': []
                }

            total = len(images)
            with_alt = sum(1 for img in images if img.get('alt'))
            with_dimensions = sum(1 for img in images if img.get('width') and img.get('height'))
            with_lazy = sum(1 for img in images if img.get('loading') == 'lazy')

            # Check for modern formats
            modern_formats = 0
            for img in images:
                src = img.get('src', '').lower()
                if any(fmt in src for fmt in ['.webp', '.avif']):
                    modern_formats += 1

            # Calculate score
            alt_score = (with_alt / total) * 30
            dim_score = (with_dimensions / total) * 30
            lazy_score = (with_lazy / total) * 20
            format_score = (modern_formats / total) * 20

            score = int(alt_score + dim_score + lazy_score + format_score)

            return {
                'score': score,
                'comment': f"{total} images: {with_alt} with alt, {with_dimensions} with dimensions, {with_lazy} lazy-loaded",
                'metadata': {
                    'measurement_id': 'WI-023',
                    'total_images': total,
                    'with_alt': with_alt,
                    'with_dimensions': with_dimensions,
                    'lazy_loaded': with_lazy,
                    'modern_formats': modern_formats,
                    'execution_time_ms': int((datetime.utcnow() - start).total_seconds() * 1000)
                },
                'recommendations': [
                    'Add alt text to all images',
                    'Specify width/height attributes',
                    'Implement lazy loading',
                    'Use modern formats (WebP, AVIF)'
                ] if score < 80 else []
            }

        except Exception as e:
            logger.error(f"[WI-023] Error: {e}")
            return {'score': 0, 'comment': f"Error: {e}", 'metadata': {'measurement_id': 'WI-023'}, 'recommendations': []}
