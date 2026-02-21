"""CNT-017: Quote Usage - Blockquotes and citations"""

from typing import Dict, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from loguru import logger
from geo_data_points.measurements.base_measurement import BaseMeasurement


class QuoteUsageMeasurement(BaseMeasurement):
    """Measures use of blockquotes and citations."""

    async def measure(self, url: str, html: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start = datetime.utcnow()

        try:
            soup = BeautifulSoup(html, 'lxml')

            blockquotes = len(soup.find_all('blockquote'))
            q_tags = len(soup.find_all('q'))
            cite_tags = len(soup.find_all('cite'))

            total_quotes = blockquotes + q_tags

            # Score
            if total_quotes >= 5:
                score = 100
            elif total_quotes >= 3:
                score = 80
            elif total_quotes >= 2:
                score = 60
            elif total_quotes >= 1:
                score = 40
            else:
                score = 100  # N/A if no quotes needed

            comment = f"{total_quotes} quotes found" if total_quotes > 0 else "No quotes (may not be needed)"

            return {
                'score': score,
                'comment': comment,
                'metadata': {
                    'measurement_id': 'CNT-017',
                    'blockquotes': blockquotes,
                    'q_tags': q_tags,
                    'cite_tags': cite_tags,
                    'execution_time_ms': int((datetime.utcnow() - start).total_seconds() * 1000)
                },
                'recommendations': ['Add citations with <cite> tags'] if total_quotes > 0 and cite_tags == 0 else []
            }

        except Exception as e:
            logger.error(f"[CNT-017] Error: {e}")
            return {'score': 0, 'comment': f"Error: {e}", 'metadata': {'measurement_id': 'CNT-017'}, 'recommendations': []}
