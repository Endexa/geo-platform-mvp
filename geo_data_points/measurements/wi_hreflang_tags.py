"""WI-022: Hreflang Tags - International SEO"""

from typing import Dict, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from loguru import logger
from geo_data_points.measurements.base_measurement import BaseMeasurement


class HreflangTagsMeasurement(BaseMeasurement):
    """Measures hreflang implementation for international sites."""

    async def measure(self, url: str, html: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start = datetime.utcnow()

        try:
            soup = BeautifulSoup(html, 'lxml')

            # Find hreflang tags
            hreflang_links = soup.find_all('link', rel='alternate', hreflang=True)

            languages = set()
            for link in hreflang_links:
                lang = link.get('hreflang')
                if lang:
                    languages.add(lang)

            lang_count = len(languages)

            # Score
            if lang_count >= 10:
                score = 100
            elif lang_count >= 5:
                score = 85
            elif lang_count >= 3:
                score = 70
            elif lang_count >= 2:
                score = 50
            elif lang_count >= 1:
                score = 30
            else:
                score = 100  # Not applicable if no international content

            comment = f"{lang_count} language variants configured" if lang_count > 0 else "No hreflang tags (single language site)"

            return {
                'score': score,
                'comment': comment,
                'metadata': {
                    'measurement_id': 'WI-022',
                    'language_count': lang_count,
                    'languages': list(languages),
                    'execution_time_ms': int((datetime.utcnow() - start).total_seconds() * 1000)
                },
                'recommendations': ['Add hreflang tags for international variants'] if lang_count == 0 and metadata and metadata.get('is_international') else []
            }

        except Exception as e:
            logger.error(f"[WI-022] Error: {e}")
            return {'score': 0, 'comment': f"Error: {e}", 'metadata': {'measurement_id': 'WI-022'}, 'recommendations': []}
