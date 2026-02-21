"""SEO-009: Local SEO"""

from typing import Dict, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from loguru import logger
from geo_data_points.measurements.base_measurement import BaseMeasurement


class LocalSEOMeasurement(BaseMeasurement):
    """Measures local SEO indicators (NAP, local schema, etc.)."""

    async def measure(self, url: str, html: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start = datetime.utcnow()

        try:
            soup = BeautifulSoup(html, 'lxml')

            # Check for local business schema
            scripts = soup.find_all('script', type='application/ld+json')
            has_local_business = False
            for script in scripts:
                if script.string and 'localbusiness' in script.string.lower():
                    has_local_business = True
                    break

            # Check for address/contact info
            text = soup.get_text().lower()
            has_phone = 'phone' in text or 'tel' in text
            has_address = 'address' in text or 'street' in text
            has_hours = 'hours' in text or 'open' in text

            # Calculate score
            points = 0
            if has_local_business:
                points += 40
            if has_phone:
                points += 20
            if has_address:
                points += 20
            if has_hours:
                points += 20

            score = points

            return {
                'score': score,
                'comment': f"Local SEO score: {score}/100",
                'metadata': {
                    'measurement_id': 'SEO-009',
                    'has_local_business_schema': has_local_business,
                    'has_phone': has_phone,
                    'has_address': has_address,
                    'has_hours': has_hours,
                    'execution_time_ms': int((datetime.utcnow() - start).total_seconds() * 1000)
                },
                'recommendations': [
                    'Add LocalBusiness schema markup',
                    'Include complete NAP (Name, Address, Phone)',
                    'Add business hours information'
                ] if score < 80 else []
            }

        except Exception as e:
            logger.error(f"[SEO-009] Error: {e}")
            return {'score': 0, 'comment': f"Error: {e}", 'metadata': {'measurement_id': 'SEO-009'}, 'recommendations': []}
