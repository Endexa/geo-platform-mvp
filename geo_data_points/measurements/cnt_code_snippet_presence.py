"""CNT-016: Code Snippet Presence"""

from typing import Dict, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from loguru import logger
from geo_data_points.measurements.base_measurement import BaseMeasurement


class CodeSnippetPresenceMeasurement(BaseMeasurement):
    """Measures presence and formatting of code snippets."""

    async def measure(self, url: str, html: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start = datetime.utcnow()

        try:
            soup = BeautifulSoup(html, 'lxml')

            # Count code elements
            code_tags = len(soup.find_all('code'))
            pre_tags = len(soup.find_all('pre'))
            code_blocks = len(soup.find_all('pre', class_=lambda x: x and 'code' in x.lower() if x else False))

            total_code = code_tags + pre_tags

            # Score
            if total_code >= 10:
                score = 100
            elif total_code >= 5:
                score = 80
            elif total_code >= 3:
                score = 60
            elif total_code >= 1:
                score = 40
            else:
                score = 100  # N/A for non-technical content

            comment = f"{total_code} code snippets found" if total_code > 0 else "No code snippets (may not be technical content)"

            return {
                'score': score,
                'comment': comment,
                'metadata': {
                    'measurement_id': 'CNT-016',
                    'code_tags': code_tags,
                    'pre_tags': pre_tags,
                    'execution_time_ms': int((datetime.utcnow() - start).total_seconds() * 1000)
                },
                'recommendations': ['Use <code> and <pre> tags for better code presentation'] if total_code > 0 and code_tags == 0 else []
            }

        except Exception as e:
            logger.error(f"[CNT-016] Error: {e}")
            return {'score': 0, 'comment': f"Error: {e}", 'metadata': {'measurement_id': 'CNT-016'}, 'recommendations': []}
