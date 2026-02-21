"""CNT-021: Actionable Content (CTAs)"""

from typing import Dict, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from loguru import logger
from geo_data_points.measurements.base_measurement import BaseMeasurement


class ActionableContentMeasurement(BaseMeasurement):
    """Measures calls-to-action and actionable content."""

    async def measure(self, url: str, html: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start = datetime.utcnow()

        try:
            soup = BeautifulSoup(html, 'lxml')

            # Count buttons and CTAs
            buttons = len(soup.find_all('button'))
            cta_links = len(soup.find_all('a', class_=lambda x: x and ('btn' in x.lower() or 'cta' in x.lower()) if x else False))
            forms = len(soup.find_all('form'))

            total_ctas = buttons + cta_links + forms

            # Score
            if total_ctas >= 5:
                score = 100
            elif total_ctas >= 3:
                score = 80
            elif total_ctas >= 1:
                score = 60
            else:
                score = 40

            return {
                'score': score,
                'comment': f"{total_ctas} actionable elements ({buttons} buttons, {cta_links} CTA links, {forms} forms)",
                'metadata': {
                    'measurement_id': 'CNT-021',
                    'buttons': buttons,
                    'cta_links': cta_links,
                    'forms': forms,
                    'total_ctas': total_ctas,
                    'execution_time_ms': int((datetime.utcnow() - start).total_seconds() * 1000)
                },
                'recommendations': ['Add clear calls-to-action'] if total_ctas < 3 else []
            }

        except Exception as e:
            logger.error(f"[CNT-021] Error: {e}")
            return {'score': 0, 'comment': f"Error: {e}", 'metadata': {'measurement_id': 'CNT-021'}, 'recommendations': []}
