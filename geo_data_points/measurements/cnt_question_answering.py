"""CNT-022: Question Answering Format"""

from typing import Dict, Any, Optional
from datetime import datetime
import re
from bs4 import BeautifulSoup
from loguru import logger
from geo_data_points.measurements.base_measurement import BaseMeasurement


class QuestionAnsweringMeasurement(BaseMeasurement):
    """Measures Q&A format content (good for featured snippets)."""

    async def measure(self, url: str, html: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start = datetime.utcnow()

        try:
            soup = BeautifulSoup(html, 'lxml')
            text = soup.get_text()

            # Count question patterns
            question_patterns = [r'\?', r'how to', r'what is', r'why', r'when', r'where']
            question_count = sum(len(re.findall(pattern, text, re.IGNORECASE)) for pattern in question_patterns)

            # Score
            if question_count >= 10:
                score = 100
            elif question_count >= 5:
                score = 80
            elif question_count >= 3:
                score = 60
            elif question_count >= 1:
                score = 40
            else:
                score = 20

            return {
                'score': score,
                'comment': f"{question_count} question patterns found",
                'metadata': {
                    'measurement_id': 'CNT-022',
                    'question_count': question_count,
                    'execution_time_ms': int((datetime.utcnow() - start).total_seconds() * 1000)
                },
                'recommendations': ['Add Q&A format content for featured snippets'] if score < 60 else []
            }

        except Exception as e:
            logger.error(f"[CNT-022] Error: {e}")
            return {'score': 0, 'comment': f"Error: {e}", 'metadata': {'measurement_id': 'CNT-022'}, 'recommendations': []}
