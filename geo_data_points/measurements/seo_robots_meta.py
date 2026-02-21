"""SEO-012: Robots Meta Tags"""

from typing import Dict, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from loguru import logger
from geo_data_points.measurements.base_measurement import BaseMeasurement


class RobotsMetaMeasurement(BaseMeasurement):
    """Measures robots meta tag configuration."""

    async def measure(self, url: str, html: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start = datetime.utcnow()

        try:
            soup = BeautifulSoup(html, 'lxml')

            # Check for robots meta tag
            robots_meta = soup.find('meta', attrs={'name': 'robots'})

            if not robots_meta:
                # No robots tag = default (index, follow) = good
                return {
                    'score': 100,
                    'comment': "No robots meta tag (default: index, follow)",
                    'metadata': {
                        'measurement_id': 'SEO-012',
                        'has_robots_tag': False,
                        'is_indexable': True,
                        'execution_time_ms': int((datetime.utcnow() - start).total_seconds() * 1000)
                    },
                    'recommendations': []
                }

            content = (robots_meta.get('content', '') or '').lower()

            # Check directives
            is_noindex = 'noindex' in content
            is_nofollow = 'nofollow' in content
            is_noimageindex = 'noimageindex' in content

            if is_noindex:
                score = 20  # Page blocked from indexing
                comment = "⚠️ Page blocked from indexing (noindex)"
            elif is_nofollow:
                score = 60
                comment = "Links set to nofollow"
            else:
                score = 100
                comment = "Robots meta tag allows indexing"

            return {
                'score': score,
                'comment': comment,
                'metadata': {
                    'measurement_id': 'SEO-012',
                    'has_robots_tag': True,
                    'robots_content': content,
                    'is_noindex': is_noindex,
                    'is_nofollow': is_nofollow,
                    'execution_time_ms': int((datetime.utcnow() - start).total_seconds() * 1000)
                },
                'recommendations': ['Remove noindex if page should be indexed'] if is_noindex else []
            }

        except Exception as e:
            logger.error(f"[SEO-012] Error: {e}")
            return {'score': 0, 'comment': f"Error: {e}", 'metadata': {'measurement_id': 'SEO-012'}, 'recommendations': []}
