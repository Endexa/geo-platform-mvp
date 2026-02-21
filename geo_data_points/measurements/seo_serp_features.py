"""
SEO-007: SERP Features

Measures presence in enhanced search result features (featured snippets,
knowledge panels, image packs, etc.)
"""

from typing import Dict, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from loguru import logger

from geo_data_points.measurements.base_measurement import BaseMeasurement


class SERPFeaturesMeasurement(BaseMeasurement):
    """Measures SERP feature presence and richness."""

    async def measure(
        self,
        url: str,
        html: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Measure SERP feature presence."""
        execution_start = datetime.utcnow()

        try:
            # Check if data provided in metadata
            if metadata and 'serp_features' in metadata:
                features = metadata['serp_features']
            else:
                # Analyze HTML for structured data that enables SERP features
                features = self._analyze_serp_enablers(html)

            # Calculate score
            feature_count = len([f for f in features.values() if f])
            max_features = len(features)

            score = int((feature_count / max_features) * 100) if max_features > 0 else 0

            # Generate comment
            active_features = [name for name, present in features.items() if present]
            if score >= 80:
                comment = f"Excellent SERP feature coverage with {len(active_features)} active features"
            elif score >= 60:
                comment = f"Good SERP presence with {len(active_features)} features enabled"
            elif score >= 40:
                comment = f"Moderate SERP features: {len(active_features)} of {max_features} present"
            else:
                comment = f"Limited SERP features: only {len(active_features)} enabled"

            return {
                'score': score,
                'comment': comment,
                'metadata': {
                    'measurement_id': 'SEO-007',
                    'measurement_name': 'SERP Features',
                    'url': url,
                    'execution_time_ms': self._calc_execution_time(execution_start),
                    'features': features,
                    'active_count': len(active_features)
                },
                'recommendations': self._get_recommendations(features)
            }

        except Exception as e:
            logger.error(f"[SEO-007] Error: {str(e)}")
            return {
                'score': 0,
                'comment': f"Error measuring SERP features: {str(e)}",
                'metadata': {
                    'measurement_id': 'SEO-007',
                    'error': str(e)
                },
                'recommendations': []
            }

    def _analyze_serp_enablers(self, html: str) -> Dict[str, bool]:
        """Check HTML for structured data that enables SERP features."""
        soup = BeautifulSoup(html, 'lxml')

        features = {
            'schema_markup': False,
            'faq_schema': False,
            'howto_schema': False,
            'recipe_schema': False,
            'review_schema': False,
            'video_schema': False,
            'breadcrumb_schema': False,
            'organization_schema': False
        }

        # Check for JSON-LD structured data
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            if not script.string:
                continue

            content = script.string.lower()

            if '@type' in content or '@graph' in content:
                features['schema_markup'] = True
            if 'faqpage' in content:
                features['faq_schema'] = True
            if 'howto' in content:
                features['howto_schema'] = True
            if 'recipe' in content:
                features['recipe_schema'] = True
            if 'review' in content or 'aggregaterating' in content:
                features['review_schema'] = True
            if 'videoobject' in content:
                features['video_schema'] = True
            if 'breadcrumblist' in content:
                features['breadcrumb_schema'] = True
            if 'organization' in content:
                features['organization_schema'] = True

        return features

    def _get_recommendations(self, features: Dict[str, bool]) -> list:
        """Generate recommendations based on missing features."""
        recommendations = []

        if not features.get('schema_markup'):
            recommendations.append("Add structured data markup to enable rich results")

        if not features.get('faq_schema'):
            recommendations.append("Add FAQ schema for FAQ-rich snippets")

        if not features.get('review_schema'):
            recommendations.append("Add review/rating schema if applicable")

        if not features.get('breadcrumb_schema'):
            recommendations.append("Add breadcrumb schema for enhanced navigation display")

        return recommendations

    def _calc_execution_time(self, start_time: datetime) -> int:
        """Calculate execution time in milliseconds."""
        delta = datetime.utcnow() - start_time
        return int(delta.total_seconds() * 1000)
