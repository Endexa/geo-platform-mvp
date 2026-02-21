"""CNT-018: External Links Quality"""

from typing import Dict, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from loguru import logger
from geo_data_points.measurements.base_measurement import BaseMeasurement


class ExternalLinksMeasurement(BaseMeasurement):
    """Measures quality and quantity of external links."""

    async def measure(self, url: str, html: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start = datetime.utcnow()

        try:
            soup = BeautifulSoup(html, 'lxml')
            domain = urlparse(url).netloc

            # Find all links
            all_links = soup.find_all('a', href=True)

            external_links = []
            for link in all_links:
                href = link['href']
                if href.startswith('http') and domain not in href:
                    external_links.append(href)

            external_count = len(external_links)

            # Check for nofollow
            nofollow_count = sum(1 for link in soup.find_all('a', href=True, rel=lambda r: r and 'nofollow' in r))

            # Score based on external link presence
            if 5 <= external_count <= 20:
                score = 100
            elif 3 <= external_count <= 30:
                score = 80
            elif 1 <= external_count <= 40:
                score = 60
            elif external_count > 40:
                score = 40  # Too many external links
            else:
                score = 50  # No external links

            return {
                'score': score,
                'comment': f"{external_count} external links ({nofollow_count} with nofollow)",
                'metadata': {
                    'measurement_id': 'CNT-018',
                    'external_links_count': external_count,
                    'nofollow_count': nofollow_count,
                    'execution_time_ms': int((datetime.utcnow() - start).total_seconds() * 1000)
                },
                'recommendations': [
                    'Add relevant external links to authoritative sources',
                    'Use nofollow for untrusted links'
                ] if external_count < 3 or (external_count > 0 and nofollow_count == 0) else []
            }

        except Exception as e:
            logger.error(f"[CNT-018] Error: {e}")
            return {'score': 0, 'comment': f"Error: {e}", 'metadata': {'measurement_id': 'CNT-018'}, 'recommendations': []}
