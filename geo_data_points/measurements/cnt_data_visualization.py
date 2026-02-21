"""CNT-023: Data Visualization"""

from typing import Dict, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from loguru import logger
from geo_data_points.measurements.base_measurement import BaseMeasurement


class DataVisualizationMeasurement(BaseMeasurement):
    """Measures data visualization elements (charts, graphs, infographics)."""

    async def measure(self, url: str, html: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start = datetime.utcnow()

        try:
            soup = BeautifulSoup(html, 'lxml')

            # Check for common chart/graph indicators
            canvas_elements = len(soup.find_all('canvas'))
            svg_elements = len(soup.find_all('svg'))
            chart_classes = len(soup.find_all(class_=lambda x: x and ('chart' in x.lower() or 'graph' in x.lower()) if x else False))

            total_viz = canvas_elements + svg_elements + chart_classes

            # Score
            if total_viz >= 5:
                score = 100
            elif total_viz >= 3:
                score = 85
            elif total_viz >= 1:
                score = 70
            else:
                score = 100  # N/A if not data-focused content

            return {
                'score': score,
                'comment': f"{total_viz} data visualization elements found",
                'metadata': {
                    'measurement_id': 'CNT-023',
                    'canvas_elements': canvas_elements,
                    'svg_elements': svg_elements,
                    'chart_classes': chart_classes,
                    'execution_time_ms': int((datetime.utcnow() - start).total_seconds() * 1000)
                },
                'recommendations': ['Add data visualizations where appropriate'] if total_viz == 0 else []
            }

        except Exception as e:
            logger.error(f"[CNT-023] Error: {e}")
            return {'score': 0, 'comment': f"Error: {e}", 'metadata': {'measurement_id': 'CNT-023'}, 'recommendations': []}
