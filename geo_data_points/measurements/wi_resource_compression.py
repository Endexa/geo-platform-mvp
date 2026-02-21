"""WI-028: Resource Compression (GZIP/Brotli)"""

from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger
from geo_data_points.measurements.base_measurement import BaseMeasurement


class ResourceCompressionMeasurement(BaseMeasurement):
    """Measures resource compression implementation."""

    async def measure(self, url: str, html: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start = datetime.utcnow()

        try:
            # Check from metadata
            has_compression = metadata.get('has_compression', False) if metadata else False
            compression_type = metadata.get('compression_type', 'none') if metadata else 'none'

            if compression_type.lower() == 'brotli':
                score = 100
            elif compression_type.lower() == 'gzip':
                score = 85
            elif has_compression:
                score = 70
            else:
                score = 30

            return {
                'score': score,
                'comment': f"Compression: {compression_type}" if compression_type != 'none' else "No compression detected",
                'metadata': {
                    'measurement_id': 'WI-028',
                    'has_compression': has_compression,
                    'compression_type': compression_type,
                    'execution_time_ms': int((datetime.utcnow() - start).total_seconds() * 1000)
                },
                'recommendations': ['Enable GZIP or Brotli compression'] if not has_compression else []
            }

        except Exception as e:
            logger.error(f"[WI-028] Error: {e}")
            return {'score': 0, 'comment': f"Error: {e}", 'metadata': {'measurement_id': 'WI-028'}, 'recommendations': []}
