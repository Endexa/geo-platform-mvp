"""
CNT-006: Word Count

Measures total word count of main content.
AI models prefer substantial, comprehensive content.
"""

from typing import Dict, Any
from geo_data_points.base import BaseMeasurement
from geo_data_points.utils.html_parser import HTMLAnalyzer
from loguru import logger


class WordCountMeasurement(BaseMeasurement):
    """Measure word count of main content."""

    def __init__(self):
        super().__init__(
            code="CNT-006",
            name="Word Count",
            description="Measures total word count of main content",
            category="Content",
            weight=0.85
        )

    async def measure(self, url: str, html: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Measure content word count.

        Scoring:
        - 100: 2000+ words (comprehensive)
        - 95: 1500-2000 words
        - 90: 1000-1500 words
        - 80: 750-1000 words
        - 70: 500-750 words
        - 50: 300-500 words
        - 30: 150-300 words
        - 10: <150 words

        Args:
            url: Target URL
            html: HTML content
            metadata: Unused

        Returns:
            Dict with score and comment
        """
        try:
            if not html:
                return {'score': 0, 'comment': 'No HTML content provided.'}

            analyzer = HTMLAnalyzer(html, url)
            main_text = analyzer.get_main_content_text()

            if not main_text:
                return {'score': 0, 'comment': 'No content text found.'}

            words = main_text.split()
            word_count = len(words)

            if word_count >= 2000:
                score, level = 100, "Comprehensive"
                comment = f'{level}: {word_count:,} words. Excellent depth for AI models!'
            elif word_count >= 1500:
                score, level = 95, "Very Detailed"
                comment = f'{level}: {word_count:,} words. Great content depth!'
            elif word_count >= 1000:
                score, level = 90, "Detailed"
                comment = f'{level}: {word_count:,} words. Strong content length.'
            elif word_count >= 750:
                score, level = 80, "Good Length"
                comment = f'{level}: {word_count:,} words. Solid content.'
            elif word_count >= 500:
                score, level = 70, "Moderate"
                comment = f'{level}: {word_count:,} words. Consider expanding for better coverage.'
            elif word_count >= 300:
                score, level = 50, "Short"
                comment = f'{level}: {word_count:,} words. Add depth - aim for 1000+ words.'
            elif word_count >= 150:
                score, level = 30, "Very Short"
                comment = f'{level}: {word_count:,} words. Insufficient - expand significantly.'
            else:
                score, level = 10, "Minimal"
                comment = f'{level}: Only {word_count} words. Critical: Add substantial content.'

            return {'score': score, 'comment': comment}

        except Exception as e:
            logger.error(f"Error measuring word count for {url}: {str(e)}")
            return {'score': 0, 'comment': f'Measurement failed: {str(e)}'}


measurement = WordCountMeasurement()
