"""WI-029: Resource Minification"""

from typing import Dict, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from loguru import logger
from geo_data_points.measurements.base_measurement import BaseMeasurement


class MinificationMeasurement(BaseMeasurement):
    """Measures CSS/JS minification."""

    async def measure(self, url: str, html: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start = datetime.utcnow()

        try:
            soup = BeautifulSoup(html, 'lxml')

            # Check script and link tags
            scripts = soup.find_all('script', src=True)
            styles = soup.find_all('link', rel='stylesheet', href=True)

            total_resources = len(scripts) + len(styles)
            minified_resources = 0

            for script in scripts:
                src = script.get('src', '')
                if '.min.' in src:
                    minified_resources += 1

            for style in styles:
                href = style.get('href', '')
                if '.min.' in href:
                    minified_resources += 1

            if total_resources == 0:
                return {
                    'score': 100,
                    'comment': "No external resources found",
                    'metadata': {'measurement_id': 'WI-029'},
                    'recommendations': []
                }

            minified_pct = (minified_resources / total_resources) * 100
            score = int(minified_pct)

            return {
                'score': score,
                'comment': f"{minified_resources}/{total_resources} resources minified ({minified_pct:.0f}%)",
                'metadata': {
                    'measurement_id': 'WI-029',
                    'minified_resources': minified_resources,
                    'total_resources': total_resources,
                    'execution_time_ms': int((datetime.utcnow() - start).total_seconds() * 1000)
                },
                'recommendations': ['Minify CSS and JavaScript files'] if score < 80 else []
            }

        except Exception as e:
            logger.error(f"[WI-029] Error: {e}")
            return {'score': 0, 'comment': f"Error: {e}", 'metadata': {'measurement_id': 'WI-029'}, 'recommendations': []}
