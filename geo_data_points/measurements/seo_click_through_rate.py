"""SEO-008: Click-Through Rate"""

from typing import Dict, Any, Optional
from time import perf_counter
from loguru import logger
from geo_data_points.measurements.base_measurement import BaseMeasurement


class ClickThroughRateMeasurement(BaseMeasurement):
    async def measure(self, url: str, html: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start = perf_counter()

        try:
            raw_ctr = metadata.get("ctr", 0) if metadata else 0

            # normalize to float
            try:
                ctr = float(raw_ctr)
            except Exception:
                ctr = 0

            # if CTR is 0–1, assume it's a fraction → convert to %
            if 0 < ctr < 1:
                ctr *= 100

            # scoring
            if ctr >= 10:
                score = 100
            elif ctr >= 5:
                score = 80
            elif ctr >= 3:
                score = 60
            elif ctr >= 1:
                score = 40
            elif ctr > 0:
                score = 20
            else:
                score = 0

            return {
                "score": score,
                "comment": f"Average CTR: {ctr:.2f}%",
                "metadata": {
                    "measurement_id": "SEO-008",
                    "ctr": ctr,
                    "execution_time_ms": int((perf_counter() - start) * 1000),
                },
                "recommendations": (
                    ["Improve titles & meta descriptions to increase CTR"]
                    if ctr < 5 else []
                ),
            }

        except Exception as e:
            logger.error(f"[SEO-008] Error: {e}")
            return {
                "score": 0,
                "comment": f"Error: {e}",
                "metadata": {"measurement_id": "SEO-008"},
                "recommendations": [],
            }
