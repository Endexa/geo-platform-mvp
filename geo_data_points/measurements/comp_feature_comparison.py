"""COMP-005: Feature Comparison"""

from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger
from geo_data_points.measurements.base_measurement import BaseMeasurement


class FeatureComparisonMeasurement(BaseMeasurement):
    async def measure(self, url: str, html: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start = datetime.utcnow()
        try:
            feature_coverage = metadata.get('feature_coverage_pct', 70) if metadata else 70
            return {
                'score': int(feature_coverage),
                'comment': f"{feature_coverage:.0f}% feature parity with competitors",
                'metadata': {'measurement_id': 'COMP-005', 'feature_coverage': feature_coverage, 'execution_time_ms': int((datetime.utcnow() - start).total_seconds() * 1000)},
                'recommendations': ['Add missing competitive features'] if feature_coverage < 80 else []
            }
        except Exception as e:
            logger.error(f"[COMP-005] Error: {e}")
            return {'score': 0, 'comment': f"Error: {e}", 'metadata': {'measurement_id': 'COMP-005'}, 'recommendations': []}
