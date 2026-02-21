"""CNT-024: Step-by-Step Instructions"""

from typing import Dict, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from loguru import logger
from geo_data_points.measurements.base_measurement import BaseMeasurement


class StepByStepInstructionsMeasurement(BaseMeasurement):
    """Measures structured step-by-step instructional content."""

    async def measure(self, url: str, html: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start = datetime.utcnow()

        try:
            soup = BeautifulSoup(html, 'lxml')

            # Look for ordered lists (common for steps)
            ordered_lists = soup.find_all('ol')
            step_classes = soup.find_all(class_=lambda x: x and 'step' in x.lower() if x else False)

            total_step_indicators = len(ordered_lists) + len(step_classes)

            # Score
            if total_step_indicators >= 3:
                score = 100
            elif total_step_indicators >= 2:
                score = 85
            elif total_step_indicators >= 1:
                score = 70
            else:
                score = 100  # N/A if not instructional content

            return {
                'score': score,
                'comment': f"{total_step_indicators} step-by-step instruction sets found",
                'metadata': {
                    'measurement_id': 'CNT-024',
                    'ordered_lists': len(ordered_lists),
                    'step_classes': len(step_classes),
                    'execution_time_ms': int((datetime.utcnow() - start).total_seconds() * 1000)
                },
                'recommendations': ['Structure instructions as numbered steps'] if total_step_indicators == 0 else []
            }

        except Exception as e:
            logger.error(f"[CNT-024] Error: {e}")
            return {'score': 0, 'comment': f"Error: {e}", 'metadata': {'measurement_id': 'CNT-024'}, 'recommendations': []}
