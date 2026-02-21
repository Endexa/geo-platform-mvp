"""SEO-011: URL Structure Quality"""

from typing import Dict, Any, Optional
from datetime import datetime
from urllib.parse import urlparse
from loguru import logger
from geo_data_points.measurements.base_measurement import BaseMeasurement


class URLStructureMeasurement(BaseMeasurement):
    """Measures URL structure quality (readability, keywords, length)."""

    async def measure(self, url: str, html: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start = datetime.utcnow()

        try:
            parsed = urlparse(url)
            path = parsed.path

            # Check URL characteristics
            url_length = len(url)
            has_keywords = any(c.isalpha() for c in path)
            has_underscores = '_' in path
            has_params = '?' in url or '&' in url
            depth = len([p for p in path.split('/') if p])

            points = 0

            # Length check (shorter is better)
            if url_length <= 75:
                points += 25
            elif url_length <= 100:
                points += 15

            # Readable path
            if has_keywords and not has_underscores:
                points += 25

            # Clean structure
            if not has_params:
                points += 25

            # Depth (shallower is better)
            if depth <= 3:
                points += 25
            elif depth <= 5:
                points += 15

            score = points

            issues = []
            if url_length > 100:
                issues.append('URL too long')
            if has_underscores:
                issues.append('Use hyphens instead of underscores')
            if depth > 5:
                issues.append('URL too deep')

            comment = f"URL structure: {score}/100"
            if issues:
                comment += f" - Issues: {', '.join(issues)}"

            return {
                'score': score,
                'comment': comment,
                'metadata': {
                    'measurement_id': 'SEO-011',
                    'url_length': url_length,
                    'depth': depth,
                    'has_params': has_params,
                    'execution_time_ms': int((datetime.utcnow() - start).total_seconds() * 1000)
                },
                'recommendations': issues if issues else []
            }

        except Exception as e:
            logger.error(f"[SEO-011] Error: {e}")
            return {'score': 0, 'comment': f"Error: {e}", 'metadata': {'measurement_id': 'SEO-011'}, 'recommendations': []}
