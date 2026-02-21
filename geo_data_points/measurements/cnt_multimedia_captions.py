"""CNT-020: Multimedia Captions/Transcripts"""

from typing import Dict, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from loguru import logger
from geo_data_points.measurements.base_measurement import BaseMeasurement


class MultimediaCaptionsMeasurement(BaseMeasurement):
    """Measures captions and transcripts for video/audio content."""

    async def measure(self, url: str, html: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start = datetime.utcnow()

        try:
            soup = BeautifulSoup(html, 'lxml')

            videos = soup.find_all('video')
            audios = soup.find_all('audio')
            total_media = len(videos) + len(audios)

            if total_media == 0:
                return {
                    'score': 100,
                    'comment': "No video/audio content found",
                    'metadata': {'measurement_id': 'CNT-020'},
                    'recommendations': []
                }

            # Check for track elements (captions/subtitles)
            videos_with_tracks = sum(1 for v in videos if v.find('track'))
            audios_with_tracks = sum(1 for a in audios if a.find('track'))
            total_with_tracks = videos_with_tracks + audios_with_tracks

            caption_pct = (total_with_tracks / total_media) * 100 if total_media > 0 else 0
            score = int(caption_pct)

            return {
                'score': score,
                'comment': f"{total_with_tracks}/{total_media} media elements have captions/transcripts ({caption_pct:.0f}%)",
                'metadata': {
                    'measurement_id': 'CNT-020',
                    'total_media': total_media,
                    'with_captions': total_with_tracks,
                    'execution_time_ms': int((datetime.utcnow() - start).total_seconds() * 1000)
                },
                'recommendations': ['Add captions/transcripts to video and audio content'] if score < 100 else []
            }

        except Exception as e:
            logger.error(f"[CNT-020] Error: {e}")
            return {'score': 0, 'comment': f"Error: {e}", 'metadata': {'measurement_id': 'CNT-020'}, 'recommendations': []}
