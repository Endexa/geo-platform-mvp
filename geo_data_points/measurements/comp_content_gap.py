"""COMP-003: Content Gap Analysis"""

from typing import Dict, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from loguru import logger
from geo_data_points.measurements.base_measurement import BaseMeasurement


class ContentGapMeasurement(BaseMeasurement):
    """Analyzes content coverage compared to topic expectations."""

    async def measure(self, url: str, html: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start = datetime.utcnow()

        try:
            soup = BeautifulSoup(html, 'lxml')

            # Extract text and basic metrics
            text = soup.get_text(separator=' ', strip=True)
            word_count = len(text.split())
            headings = soup.find_all(['h2', 'h3'])
            heading_count = len(headings)

            # Content comprehensiveness metrics
            sections = heading_count
            lists = len(soup.find_all(['ul', 'ol']))
            images = len(soup.find_all('img'))
            tables = len(soup.find_all('table'))

            # Score based on content depth
            content_score = min(100, (word_count // 20))  # Up to 2000 words
            structure_score = min(100, (sections * 10))  # Up to 10 sections
            media_score = min(100, ((images + tables) * 10))  # Up to 10 media elements
            list_score = min(100, (lists * 20))  # Up to 5 lists

            score = int((content_score * 0.4) + (structure_score * 0.3) + (media_score * 0.2) + (list_score * 0.1))

            return {
                'score': score,
                'comment': f"Content depth: {word_count} words, {sections} sections, {images + tables} media",
                'metadata': {
                    'measurement_id': 'COMP-003',
                    'word_count': word_count,
                    'sections': sections,
                    'media_elements': images + tables,
                    'lists': lists,
                    'execution_time_ms': int((datetime.utcnow() - start).total_seconds() * 1000)
                },
                'recommendations': ['Expand content coverage', 'Add more sections', 'Include more media'] if score < 70 else []
            }

        except Exception as e:
            logger.error(f"[COMP-003] Error: {e}")
            return {'score': 0, 'comment': f"Error: {e}", 'metadata': {'measurement_id': 'COMP-003'}, 'recommendations': []}
