"""UX-007: Mobile-Friendly Test"""

from typing import Dict, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from loguru import logger
from geo_data_points.measurements.base_measurement import BaseMeasurement


class MobileFriendlyTestMeasurement(BaseMeasurement):
    """Measures mobile-friendliness indicators."""

    async def measure(self, url: str, html: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start = datetime.utcnow()

        try:
            soup = BeautifulSoup(html, 'lxml')

            # Check mobile indicators
            viewport_meta = soup.find('meta', attrs={'name': 'viewport'})
            has_viewport = viewport_meta is not None

            # Check responsive CSS
            style_tags = soup.find_all('style')
            has_media_queries = any('@media' in (tag.string or '') for tag in style_tags)

            # Check for mobile-specific tags
            mobile_optimized = soup.find('meta', attrs={'name': 'mobile-web-app-capable'})

            points = 0
            if has_viewport:
                points += 50
            if has_media_queries:
                points += 30
            if mobile_optimized:
                points += 20

            score = points

            issues = []
            if not has_viewport:
                issues.append('Missing viewport meta tag')
            if not has_media_queries:
                issues.append('No media queries detected')

            comment = f"Mobile-friendly score: {score}/100"
            if issues:
                comment += f" - Issues: {', '.join(issues)}"

            return {
                'score': score,
                'comment': comment,
                'metadata': {
                    'measurement_id': 'UX-007',
                    'has_viewport': has_viewport,
                    'has_media_queries': has_media_queries,
                    'execution_time_ms': int((datetime.utcnow() - start).total_seconds() * 1000)
                },
                'recommendations': issues if issues else []
            }

        except Exception as e:
            logger.error(f"[UX-007] Error: {e}")
            return {'score': 0, 'comment': f"Error: {e}", 'metadata': {'measurement_id': 'UX-007'}, 'recommendations': []}
