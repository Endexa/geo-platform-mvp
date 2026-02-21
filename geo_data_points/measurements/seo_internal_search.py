"""SEO-010: Internal Search Functionality"""

from typing import Dict, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from loguru import logger
from geo_data_points.measurements.base_measurement import BaseMeasurement


class InternalSearchMeasurement(BaseMeasurement):
    """Measures presence and quality of internal search."""

    async def measure(self, url: str, html: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start = datetime.utcnow()

        try:
            soup = BeautifulSoup(html, 'lxml')

            # Look for search forms
            search_forms = soup.find_all('form', attrs={'role': 'search'})
            search_inputs = soup.find_all('input', attrs={'type': 'search'})
            search_classes = soup.find_all(class_=lambda x: x and 'search' in x.lower() if x else False)

            has_search = len(search_forms) > 0 or len(search_inputs) > 0 or len(search_classes) > 0

            # Check for search schema
            scripts = soup.find_all('script', type='application/ld+json')
            has_search_action = any(
                script.string and 'searchaction' in script.string.lower()
                for script in scripts if script.string
            )

            points = 0
            if has_search:
                points += 60
            if has_search_action:
                points += 40

            score = points

            return {
                'score': score,
                'comment': f"Internal search {'present' if has_search else 'not found'}",
                'metadata': {
                    'measurement_id': 'SEO-010',
                    'has_search': has_search,
                    'has_search_action_schema': has_search_action,
                    'execution_time_ms': int((datetime.utcnow() - start).total_seconds() * 1000)
                },
                'recommendations': [
                    'Add internal search functionality',
                    'Implement SearchAction schema markup'
                ] if score < 80 else []
            }

        except Exception as e:
            logger.error(f"[SEO-010] Error: {e}")
            return {'score': 0, 'comment': f"Error: {e}", 'metadata': {'measurement_id': 'SEO-010'}, 'recommendations': []}
