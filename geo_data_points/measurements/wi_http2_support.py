"""WI-025: HTTP/2 Support"""

from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger
from geo_data_points.measurements.base_measurement import BaseMeasurement


class HTTP2SupportMeasurement(BaseMeasurement):
    """Measures HTTP/2 protocol support."""

    async def measure(self, url: str, html: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start = datetime.utcnow()

        try:
            # Check from metadata
            http2_enabled = metadata.get('http2_enabled', False) if metadata else False

            score = 100 if http2_enabled else 50

            return {
                'score': score,
                'comment': "HTTP/2 enabled" if http2_enabled else "HTTP/2 not detected",
                'metadata': {
                    'measurement_id': 'WI-025',
                    'http2_enabled': http2_enabled,
                    'execution_time_ms': int((datetime.utcnow() - start).total_seconds() * 1000)
                },
                'recommendations': ['Enable HTTP/2 for better performance'] if not http2_enabled else []
            }

        except Exception as e:
            logger.error(f"[WI-025] Error: {e}")
            return {'score': 0, 'comment': f"Error: {e}", 'metadata': {'measurement_id': 'WI-025'}, 'recommendations': []}
