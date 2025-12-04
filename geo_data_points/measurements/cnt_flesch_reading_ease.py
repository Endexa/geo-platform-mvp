"""
CNT-002: Flesch Reading Ease

Measures content readability using Flesch Reading Ease score.
AI models favor clear, accessible content that's easy to understand and cite.
"""

from typing import Dict, Any
from geo_data_points.base import BaseMeasurement
from geo_data_points.utils.html_parser import HTMLAnalyzer
from geo_data_points.utils.content_analyzer import ContentAnalyzer
from loguru import logger


class FleschReadingEaseMeasurement(BaseMeasurement):
    """Measure content readability with Flesch Reading Ease."""

    def __init__(self):
        super().__init__(
            code="CNT-002",
            name="Flesch Reading Ease",
            description="Measures content readability using Flesch Reading Ease score (0-100)",
            category="Content",
            weight=0.75  # Important for content accessibility
        )

    async def measure(self, url: str, html: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Measure Flesch Reading Ease score.

        Flesch Score Interpretation:
        - 90-100: Very Easy (5th grade)
        - 80-89: Easy (6th grade)
        - 70-79: Fairly Easy (7th grade)
        - 60-69: Standard (8th-9th grade)
        - 50-59: Fairly Difficult (10th-12th grade)
        - 30-49: Difficult (College)
        - 0-29: Very Difficult (College graduate)

        Scoring:
        - 100: Optimal range (60-80) - accessible yet professional
        - 90: Good range (50-90) - readable
        - 70: Acceptable (40-50 or 80-90)
        - 50: Challenging (<40 or >90)
        - 0: Insufficient content

        Args:
            url: Target URL to analyze
            html: HTML content to parse
            metadata: Unused

        Returns:
            Dict with score (0-100) and detailed comment
        """
        try:
            if not html:
                return {
                    'score': 0,
                    'comment': 'No HTML content provided for analysis.'
                }

            # Extract main content text
            analyzer = HTMLAnalyzer(html, url)
            main_text = analyzer.get_main_content_text()

            if not main_text or len(main_text.strip()) < 100:
                return {
                    'score': 0,
                    'comment': 'Insufficient content for readability analysis (<100 chars). Add at least 100 words for meaningful analysis.'
                }

            # Analyze readability
            content_analyzer = ContentAnalyzer(main_text)

            try:
                flesch_score = content_analyzer.get_flesch_reading_ease()
            except Exception as e:
                return {
                    'score': 0,
                    'comment': f'Cannot calculate Flesch score: {str(e)}. Ensure content has proper sentences and words.'
                }

            # Interpret Flesch score
            if flesch_score >= 90:
                reading_level = "Very Easy (5th grade)"
                difficulty = "very easy"
            elif flesch_score >= 80:
                reading_level = "Easy (6th grade)"
                difficulty = "easy"
            elif flesch_score >= 70:
                reading_level = "Fairly Easy (7th grade)"
                difficulty = "fairly easy"
            elif flesch_score >= 60:
                reading_level = "Standard (8th-9th grade)"
                difficulty = "standard"
            elif flesch_score >= 50:
                reading_level = "Fairly Difficult (10th-12th grade)"
                difficulty = "fairly difficult"
            elif flesch_score >= 30:
                reading_level = "Difficult (College level)"
                difficulty = "difficult"
            else:
                reading_level = "Very Difficult (College graduate)"
                difficulty = "very difficult"

            # Calculate GEO score
            # Optimal: 60-80 (Standard to Fairly Easy)
            # Good: 50-90 (Still readable)
            # Acceptable: 40-50 or 80-90
            # Poor: <40 or >90

            if 60 <= flesch_score <= 80:
                geo_score = 100
                comment = f'Optimal readability: Flesch score {flesch_score:.1f} ({reading_level}). Perfect balance of accessibility and professionalism for AI citation.'
            elif 50 <= flesch_score < 60:
                geo_score = 90
                comment = f'Good readability: Flesch score {flesch_score:.1f} ({reading_level}). Slightly formal but still accessible for AI models.'
            elif 80 < flesch_score <= 90:
                geo_score = 90
                comment = f'Good readability: Flesch score {flesch_score:.1f} ({reading_level}). Very accessible - suitable for broad AI audiences.'
            elif 40 <= flesch_score < 50:
                geo_score = 70
                comment = f'Acceptable readability: Flesch score {flesch_score:.1f} ({reading_level}). Content is {difficulty}. Consider simplifying for better AI comprehension.'
            elif 90 < flesch_score <= 100:
                geo_score = 70
                comment = f'Acceptable readability: Flesch score {flesch_score:.1f} ({reading_level}). Content might be oversimplified. Add depth for professional AI citation.'
            elif 30 <= flesch_score < 40:
                geo_score = 50
                comment = f'Challenging readability: Flesch score {flesch_score:.1f} ({reading_level}). Content is {difficulty}. Simplify sentences and use shorter words for better AI accessibility.'
            else:
                geo_score = 30
                comment = f'Poor readability: Flesch score {flesch_score:.1f} ({reading_level}). Content is {difficulty}. Significantly simplify for AI models - use shorter sentences and common vocabulary.'

            # Add specific recommendations
            if flesch_score < 60:
                avg_sentence_len = content_analyzer.get_average_sentence_length()
                if avg_sentence_len > 25:
                    comment += f' Tip: Break long sentences (avg: {avg_sentence_len:.1f} words).'
                else:
                    comment += ' Tip: Use simpler vocabulary and more common words.'
            elif flesch_score > 80:
                word_count = len(main_text.split())
                if word_count < 300:
                    comment += ' Tip: Add more depth and detail to content.'

            return {
                'score': geo_score,
                'comment': comment
            }

        except Exception as e:
            logger.error(f"Error measuring Flesch Reading Ease for {url}: {str(e)}")
            return {
                'score': 0,
                'comment': f'Measurement failed: {str(e)}'
            }


# Export for orchestrator
measurement = FleschReadingEaseMeasurement()
