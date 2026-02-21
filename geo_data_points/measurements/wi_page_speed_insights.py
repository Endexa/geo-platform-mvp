"""WI-024: Page Speed Insights Score"""

from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger
from geo_data_points.measurements.base_measurement import BaseMeasurement


class PageSpeedInsightsMeasurement(BaseMeasurement):
    """Measures PageSpeed Insights performance score."""

    async def measure(self, url: str, html: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start = datetime.utcnow()

        try:
            # Get PSI score from metadata (0-100)
            psi_score = metadata.get('psi_score', 50) if metadata else 50

            # Score maps directly to PSI
            score = int(psi_score)

            if score >= 90:
                grade = "Excellent"
            elif score >= 75:
                grade = "Good"
            elif score >= 50:
                grade = "Needs Improvement"
            else:
                grade = "Poor"

            return {
                'score': score,
                'comment': f"PageSpeed Insights: {score}/100 ({grade})",
                'metadata': {
                    'measurement_id': 'WI-024',
                    'psi_score': psi_score,
                    'grade': grade,
                    'execution_time_ms': int((datetime.utcnow() - start).total_seconds() * 1000)
                },
                'recommendations': [
                    'Optimize images and resources',
                    'Minimize JavaScript',
                    'Enable compression'
                ] if score < 75 else []
            }

        except Exception as e:
            logger.error(f"[WI-024] Error: {e}")
            return {'score': 0, 'comment': f"Error: {e}", 'metadata': {'measurement_id': 'WI-024'}, 'recommendations': []}
