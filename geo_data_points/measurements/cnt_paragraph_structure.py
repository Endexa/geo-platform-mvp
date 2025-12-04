"""
CNT-010: Paragraph Structure

Analyzes paragraph structure for optimal readability and scannability.
Well-structured paragraphs improve both user experience and AI content extraction.
"""

from typing import Dict, Any
from geo_data_points.base import BaseMeasurement
from geo_data_points.utils.html_parser import HTMLAnalyzer
from geo_data_points.utils.content_analyzer import ContentAnalyzer
from loguru import logger


class ParagraphStructureMeasurement(BaseMeasurement):
    """Analyze paragraph structure quality."""

    def __init__(self):
        super().__init__(
            code="CNT-010",
            name="Paragraph Structure",
            description="Analyzes paragraph structure for optimal readability and scannability",
            category="Content",
            weight=0.70  # Important for readability
        )

    async def measure(self, url: str, html: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Measure paragraph structure quality.

        Scoring:
        - 100: Ideal paragraph structure (50-150 words avg, good variety, 10+ paragraphs)
        - 90: Good structure (40-160 words avg, adequate variety)
        - 80: Acceptable structure (some issues but readable)
        - 70: Moderate structure (paragraphs too long or too short)
        - 50: Poor structure (very long paragraphs or wall of text)
        - 0: No proper paragraph structure

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

            # Extract main content
            analyzer = HTMLAnalyzer(html, url)
            main_text = analyzer.get_main_content_text()

            if not main_text or len(main_text.strip()) < 100:
                return {
                    'score': 0,
                    'comment': 'Insufficient content for paragraph analysis (<100 chars).'
                }

            # Analyze content structure
            content_analyzer = ContentAnalyzer(main_text)

            # Get paragraph metrics
            paragraph_count = content_analyzer.get_paragraph_count()
            avg_paragraph_length = content_analyzer.get_average_paragraph_length()

            if paragraph_count == 0:
                return {
                    'score': 0,
                    'comment': 'No paragraph structure detected. Break content into logical paragraphs (50-150 words each) for better readability and AI comprehension.'
                }

            # Get paragraph lengths distribution
            paragraphs = main_text.split('\n\n')
            paragraphs = [p.strip() for p in paragraphs if p.strip()]

            if len(paragraphs) == 0:
                # Try single newline split
                paragraphs = main_text.split('\n')
                paragraphs = [p.strip() for p in paragraphs if p.strip() and len(p.split()) > 5]

            if len(paragraphs) == 0:
                return {
                    'score': 0,
                    'comment': 'No paragraph structure detected. Add line breaks between paragraphs.'
                }

            # Calculate paragraph word counts
            paragraph_word_counts = [len(p.split()) for p in paragraphs]
            total_words = sum(paragraph_word_counts)

            if total_words < 100:
                return {
                    'score': 20,
                    'comment': f'Very short content ({total_words} words in {len(paragraphs)} paragraphs). Expand content significantly.'
                }

            # Calculate statistics
            avg_words = sum(paragraph_word_counts) / len(paragraph_word_counts)
            min_words = min(paragraph_word_counts)
            max_words = max(paragraph_word_counts)

            # Count paragraphs by length category
            very_short = len([w for w in paragraph_word_counts if w < 20])  # < 20 words
            short = len([w for w in paragraph_word_counts if 20 <= w < 40])
            ideal = len([w for w in paragraph_word_counts if 40 <= w <= 150])
            long = len([w for w in paragraph_word_counts if 150 < w <= 250])
            very_long = len([w for w in paragraph_word_counts if w > 250])

            # ========== SCORING ==========
            score = 100
            issues = []
            features = []

            # Check average paragraph length (ideal: 50-150 words)
            if 50 <= avg_words <= 150:
                features.append(f'ideal avg length ({avg_words:.0f} words)')
            elif 40 <= avg_words < 50 or 150 < avg_words <= 160:
                score -= 10
                features.append(f'acceptable avg length ({avg_words:.0f} words)')
            elif 30 <= avg_words < 40 or 160 < avg_words <= 200:
                score -= 20
                issues.append(f'suboptimal avg length ({avg_words:.0f} words)')
            else:
                score -= 30
                if avg_words < 30:
                    issues.append(f'paragraphs too short (avg {avg_words:.0f} words, aim for 50-150)')
                else:
                    issues.append(f'paragraphs too long (avg {avg_words:.0f} words, aim for 50-150)')

            # Check for wall of text (very long paragraphs)
            if very_long > 0:
                score -= very_long * 10
                issues.append(f'{very_long} very long paragraph(s) (>250 words) - break into smaller chunks')

            # Check for too many short paragraphs
            short_ratio = (very_short + short) / len(paragraphs) if len(paragraphs) > 0 else 0
            if short_ratio > 0.5:
                score -= 15
                issues.append(f'{int(short_ratio * 100)}% paragraphs are short (<40 words) - consider combining or expanding')

            # Check paragraph count
            if len(paragraphs) >= 10:
                features.append(f'{len(paragraphs)} paragraphs (good structure)')
            elif len(paragraphs) >= 5:
                features.append(f'{len(paragraphs)} paragraphs')
            else:
                score -= 10
                issues.append(f'only {len(paragraphs)} paragraphs - add more structure for longer content')

            # Check paragraph variety (standard deviation)
            if len(paragraph_word_counts) > 1:
                mean = sum(paragraph_word_counts) / len(paragraph_word_counts)
                variance = sum((x - mean) ** 2 for x in paragraph_word_counts) / len(paragraph_word_counts)
                std_dev = variance ** 0.5

                # Good variety: std_dev between 20-60
                if 20 <= std_dev <= 60:
                    features.append('good length variety')
                elif std_dev < 20:
                    score -= 5
                    issues.append('low paragraph variety (all similar length)')
                elif std_dev > 100:
                    score -= 10
                    issues.append('excessive length variance (inconsistent structure)')

            # Cap score
            score = max(0, min(100, score))

            # ========== GENERATE COMMENT ==========
            if score >= 90:
                rating = "Excellent paragraph structure"
            elif score >= 80:
                rating = "Good paragraph structure"
            elif score >= 70:
                rating = "Acceptable paragraph structure"
            elif score >= 50:
                rating = "Poor paragraph structure"
            else:
                rating = "Very poor paragraph structure"

            comment = f'{rating}. {len(paragraphs)} paragraphs, avg {avg_words:.0f} words/paragraph (range: {min_words}-{max_words} words).'

            # Add distribution breakdown
            comment += f' Distribution: {ideal} ideal ({40}-150w), {long} long (150-250w), {very_long} very long (>250w), {short + very_short} short (<40w).'

            # Add features
            if features:
                comment += f' Features: {", ".join(features)}.'

            # Add issues
            if issues:
                comment += f' Issues: {"; ".join(issues[:2])}{"..." if len(issues) > 2 else ""}.'

            # ========== RECOMMENDATIONS ==========
            recommendations = []

            if avg_words > 150:
                recommendations.append('Break long paragraphs into 2-3 shorter ones')

            if avg_words < 50:
                recommendations.append('Expand short paragraphs with more detail')

            if very_long > 0:
                recommendations.append(f'Split {very_long} very long paragraph(s) for better scannability')

            if len(paragraphs) < 5 and total_words > 500:
                recommendations.append('Add more paragraph breaks for better structure')

            if recommendations:
                comment += f' Recommendations: {"; ".join(recommendations[:2])}.'

            # ========== CONTEXT ==========
            if score >= 85:
                comment += ' Well-structured content for both readers and AI extraction.'
            elif score >= 70:
                comment += ' Acceptable structure, minor improvements needed.'
            else:
                comment += ' Improve paragraph structure for better readability and AI comprehension. Aim for 50-150 words per paragraph.'

            return {
                'score': score,
                'comment': comment,
                'metadata': {
                    'paragraph_count': len(paragraphs),
                    'avg_words_per_paragraph': avg_words,
                    'min_words': min_words,
                    'max_words': max_words,
                    'ideal_paragraphs': ideal,
                    'long_paragraphs': long + very_long
                }
            }

        except Exception as e:
            logger.error(f"Error analyzing paragraph structure for {url}: {str(e)}")
            return {
                'score': 0,
                'comment': f'Measurement failed: {str(e)}'
            }


# Export for orchestrator
measurement = ParagraphStructureMeasurement()
