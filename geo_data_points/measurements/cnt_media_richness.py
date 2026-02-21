"""CNT-014: Media Richness - Measures diversity of media types"""

from typing import Dict, Any, Optional
from time import perf_counter
from bs4 import BeautifulSoup
from loguru import logger
from geo_data_points.measurements.base_measurement import BaseMeasurement


class MediaRichnessMeasurement(BaseMeasurement):
    async def measure(self, url: str, html: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start = perf_counter()

        try:
            soup = BeautifulSoup(html or "", "lxml")

            media_types = {
                "images": len(soup.find_all("img")),
                "videos": len(soup.find_all(["video"])),
                "iframes": len(soup.find_all("iframe")),
                "audio": len(soup.find_all("audio")),
                "svg": len(soup.find_all("svg")),
                "canvas": len(soup.find_all("canvas")),
            }

            total_media = sum(media_types.values())
            types_present = sum(1 for c in media_types.values() if c > 0)

            # simple scoring
            if types_present >= 3 and total_media >= 10:
                score = 100
            elif types_present >= 2 and total_media >= 5:
                score = 80
            elif types_present >= 2 and total_media >= 3:
                score = 60
            elif total_media >= 1:
                score = 40
            else:
                score = 0

            return {
                "score": score,
                "comment": f"{types_present} media types, {total_media} total elements",
                "metadata": {
                    "measurement_id": "CNT-014",
                    "media_types": media_types,
                    "types_present": types_present,
                    "total_media": total_media,
                    "execution_time_ms": int((perf_counter() - start) * 1000),
                },
                "recommendations": (
                    ["Add more media variety (images, videos, etc.)"] if types_present < 2 else []
                ),
            }

        except Exception as e:
            logger.error(f"[CNT-014] Error: {e}")
            return {
                "score": 0,
                "comment": f"Error: {e}",
                "metadata": {"measurement_id": "CNT-014"},
                "recommendations": [],
            }
