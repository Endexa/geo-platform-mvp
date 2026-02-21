"""WI-030: DNS Prefetch Implementation"""

from typing import Dict, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from loguru import logger
from geo_data_points.measurements.base_measurement import BaseMeasurement


class DNSPrefetchMeasurement(BaseMeasurement):
    """Measures DNS prefetch implementation for external resources."""

    async def measure(self, url: str, html: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start = datetime.utcnow()

        try:
            soup = BeautifulSoup(html, 'lxml')

            # Find DNS prefetch tags
            dns_prefetch = soup.find_all('link', rel='dns-prefetch')
            preconnect = soup.find_all('link', rel='preconnect')

            total_hints = len(dns_prefetch) + len(preconnect)

            # Score
            if total_hints >= 5:
                score = 100
            elif total_hints >= 3:
                score = 85
            elif total_hints >= 1:
                score = 70
            else:
                score = 50  # Not critical

            return {
                'score': score,
                'comment': f"{len(dns_prefetch)} DNS prefetch, {len(preconnect)} preconnect hints",
                'metadata': {
                    'measurement_id': 'WI-030',
                    'dns_prefetch_count': len(dns_prefetch),
                    'preconnect_count': len(preconnect),
                    'execution_time_ms': int((datetime.utcnow() - start).total_seconds() * 1000)
                },
                'recommendations': ['Add DNS prefetch for external domains'] if total_hints < 3 else []
            }

        except Exception as e:
            logger.error(f"[WI-030] Error: {e}")
            return {'score': 0, 'comment': f"Error: {e}", 'metadata': {'measurement_id': 'WI-030'}, 'recommendations': []}
