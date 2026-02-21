"""BV-005: Social Media Presence"""

from typing import Dict, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup
import re
from loguru import logger
from geo_data_points.measurements.base_measurement import BaseMeasurement


class SocialMediaPresenceMeasurement(BaseMeasurement):
    """Measures social media links and presence."""

    SOCIAL_PLATFORMS = {
        'twitter.com': 'Twitter',
        'x.com': 'X',
        'facebook.com': 'Facebook',
        'linkedin.com': 'LinkedIn',
        'instagram.com': 'Instagram',
        'youtube.com': 'YouTube',
        'tiktok.com': 'TikTok',
        'github.com': 'GitHub'
    }

    async def measure(self, url: str, html: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start = datetime.utcnow()

        try:
            soup = BeautifulSoup(html, 'lxml')

            # Find social media links
            platforms_found = set()
            for link in soup.find_all('a', href=True):
                href = link['href'].lower()
                for domain, platform in self.SOCIAL_PLATFORMS.items():
                    if domain in href:
                        platforms_found.add(platform)

            platform_count = len(platforms_found)

            # Score
            if platform_count >= 5:
                score = 100
            elif platform_count >= 4:
                score = 85
            elif platform_count >= 3:
                score = 70
            elif platform_count >= 2:
                score = 50
            elif platform_count >= 1:
                score = 30
            else:
                score = 0

            return {
                'score': score,
                'comment': f"{platform_count} social media platforms linked: {', '.join(sorted(platforms_found))}",
                'metadata': {
                    'measurement_id': 'BV-005',
                    'platforms': list(platforms_found),
                    'count': platform_count,
                    'execution_time_ms': int((datetime.utcnow() - start).total_seconds() * 1000)
                },
                'recommendations': ['Add more social media links'] if platform_count < 3 else []
            }

        except Exception as e:
            logger.error(f"[BV-005] Error: {e}")
            return {'score': 0, 'comment': f"Error: {e}", 'metadata': {'measurement_id': 'BV-005'}, 'recommendations': []}
