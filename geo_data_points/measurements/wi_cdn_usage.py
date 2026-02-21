"""WI-027: CDN Usage"""

from typing import Dict, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from loguru import logger
from geo_data_points.measurements.base_measurement import BaseMeasurement


class CDNUsageMeasurement(BaseMeasurement):
    """Measures Content Delivery Network usage."""

    CDN_DOMAINS = [
        'cloudflare.com', 'cloudfront.net', 'fastly.net',
        'akamai.net', 'cdn.', 'jsdelivr.net', 'unpkg.com',
        'cdnjs.cloudflare.com', 'gstatic.com', 'googleusercontent.com'
    ]

    async def measure(self, url: str, html: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start = datetime.utcnow()

        try:
            soup = BeautifulSoup(html, 'lxml')

            # Check external resources
            cdn_resources = 0
            total_resources = 0

            for tag in soup.find_all(['img', 'script', 'link'], src=True):
                src = tag.get('src', '') or tag.get('href', '')
                if src and src.startswith('http'):
                    total_resources += 1
                    if any(cdn in src for cdn in self.CDN_DOMAINS):
                        cdn_resources += 1

            if total_resources == 0:
                return {
                    'score': 100,
                    'comment': "No external resources detected",
                    'metadata': {'measurement_id': 'WI-027'},
                    'recommendations': []
                }

            cdn_pct = (cdn_resources / total_resources) * 100
            score = int(cdn_pct)

            return {
                'score': score,
                'comment': f"{cdn_resources}/{total_resources} resources served via CDN ({cdn_pct:.0f}%)",
                'metadata': {
                    'measurement_id': 'WI-027',
                    'cdn_resources': cdn_resources,
                    'total_resources': total_resources,
                    'cdn_percentage': cdn_pct,
                    'execution_time_ms': int((datetime.utcnow() - start).total_seconds() * 1000)
                },
                'recommendations': ['Consider using CDN for static assets'] if cdn_pct < 50 else []
            }

        except Exception as e:
            logger.error(f"[WI-027] Error: {e}")
            return {'score': 0, 'comment': f"Error: {e}", 'metadata': {'measurement_id': 'WI-027'}, 'recommendations': []}
