"""UX-008: Page Size"""

from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger
from geo_data_points.measurements.base_measurement import BaseMeasurement


class PageSizeMeasurement(BaseMeasurement):
    """Measures total page size (HTML + resources)."""

    async def measure(self, url: str, html: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start = datetime.utcnow()

        try:
            # Get page size from metadata (in KB)
            page_size_kb = metadata.get('page_size_kb', len(html) / 1024) if metadata else len(html) / 1024

            # Score based on size (smaller is better)
            if page_size_kb <= 500:  # Under 500KB
                score = 100
            elif page_size_kb <= 1000:  # Under 1MB
                score = 85
            elif page_size_kb <= 2000:  # Under 2MB
                score = 70
            elif page_size_kb <= 3000:  # Under 3MB
                score = 50
            else:
                score = 30

            return {
                'score': score,
                'comment': f"Page size: {page_size_kb:.1f} KB",
                'metadata': {
                    'measurement_id': 'UX-008',
                    'page_size_kb': page_size_kb,
                    'execution_time_ms': int((datetime.utcnow() - start).total_seconds() * 1000)
                },
                'recommendations': [
                    'Optimize images and compress resources',
                    'Minify CSS and JavaScript',
                    'Enable GZIP compression'
                ] if page_size_kb > 1000 else []
            }

        except Exception as e:
            logger.error(f"[UX-008] Error: {e}")
            return {'score': 0, 'comment': f"Error: {e}", 'metadata': {'measurement_id': 'UX-008'}, 'recommendations': []}
