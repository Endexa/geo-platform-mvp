"""
CNT-008: Sentiment Analysis

Analyzes content sentiment (positive, negative, neutral) using lexicon-based approach.
AI models prefer balanced, informative content over overly promotional material.
"""

from typing import Dict, Any
from geo_data_points.base import BaseMeasurement
from geo_data_points.utils.html_parser import HTMLAnalyzer
from geo_data_points.utils.content_analyzer import ContentAnalyzer
from loguru import logger


class SentimentAnalysisMeasurement(BaseMeasurement):
    """Analyze content sentiment for balance and tone."""

    def __init__(self):
        super().__init__(
            code="CNT-008",
            name="Sentiment Analysis",
            description="Analyzes content sentiment (positive, negative, neutral) for balanced tone",
            category="Content",
            weight=0.75  # Important for content tone assessment
        )

    async def measure(self, url: str, html: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Measure content sentiment balance.

        Scoring:
        - 100: Balanced sentiment (40-60% neutral, mixed pos/neg)
        - 90: Slightly positive or informative (60-75% positive/neutral)
        - 80: Moderately positive (75-85% positive)
        - 60: Very positive (>85% positive, may seem promotional)
        - 50: Overly promotional (>90% positive)
        - 70: Slightly negative (60-75% negative/neutral)
        - 40: Very negative (>75% negative)
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

            # Extract main content
            analyzer = HTMLAnalyzer(html, url)
            main_text = analyzer.get_main_content_text()

            if not main_text or len(main_text.strip()) < 100:
                return {
                    'score': 0,
                    'comment': 'Insufficient content for sentiment analysis (<100 chars).'
                }

            # Analyze sentiment
            content_analyzer = ContentAnalyzer(main_text)
            sentiment_scores = content_analyzer.get_sentiment_score()

            if not sentiment_scores:
                return {
                    'score': 0,
                    'comment': 'Could not analyze sentiment. Ensure content has meaningful text.'
                }

            # Extract sentiment components
            positive_ratio = sentiment_scores.get('positive', 0)
            negative_ratio = sentiment_scores.get('negative', 0)
            neutral_ratio = sentiment_scores.get('neutral', 0)
            compound_score = sentiment_scores.get('compound', 0)  # -1 to +1

            # Normalize ratios to percentages
            positive_pct = positive_ratio * 100
            negative_pct = negative_ratio * 100
            neutral_pct = neutral_ratio * 100

            # ========== SCORING LOGIC ==========

            # Best: Balanced, informative content (40-60% neutral with mixed sentiment)
            if 40 <= neutral_pct <= 60 and positive_pct > 20 and negative_pct > 10:
                score = 100
                tone = "Balanced"
                comment = f'{tone}: {neutral_pct:.1f}% neutral, {positive_pct:.1f}% positive, {negative_pct:.1f}% negative. Excellent balanced tone for AI credibility!'

            # Very good: Slightly positive, informative
            elif positive_pct >= 50 and positive_pct < 75 and neutral_pct >= 20:
                score = 90
                tone = "Informative-Positive"
                comment = f'{tone}: {positive_pct:.1f}% positive, {neutral_pct:.1f}% neutral, {negative_pct:.1f}% negative. Professional, engaging tone suitable for AI citation.'

            # Good: Moderately positive
            elif positive_pct >= 60 and positive_pct < 85:
                score = 80
                tone = "Positive"
                comment = f'{tone}: {positive_pct:.1f}% positive, {neutral_pct:.1f}% neutral. Engaging content, slightly promotional but acceptable.'

            # Acceptable: Very positive (may seem promotional)
            elif positive_pct >= 85 and positive_pct < 90:
                score = 60
                tone = "Very Positive"
                comment = f'{tone}: {positive_pct:.1f}% positive. Content may seem promotional. Add neutral, factual information for better AI credibility.'

            # Problematic: Overly promotional
            elif positive_pct >= 90:
                score = 50
                tone = "Overly Promotional"
                comment = f'{tone}: {positive_pct:.1f}% positive. Content appears highly promotional. AI models prefer balanced, informative content. Add objective facts and neutral analysis.'

            # Acceptable: Slightly negative (critical analysis, reviews)
            elif negative_pct >= 30 and negative_pct < 50:
                score = 70
                tone = "Critical"
                comment = f'{tone}: {negative_pct:.1f}% negative, {neutral_pct:.1f}% neutral. Critical analysis is valuable. Ensure constructive tone with solutions.'

            # Problematic: Very negative
            elif negative_pct >= 50:
                score = 40
                tone = "Very Negative"
                comment = f'{tone}: {negative_pct:.1f}% negative. Overly critical content. Balance with positive aspects and constructive recommendations.'

            # Very neutral: Possibly dry or technical
            elif neutral_pct >= 80:
                score = 85
                tone = "Highly Neutral"
                comment = f'{tone}: {neutral_pct:.1f}% neutral. Very objective, factual content. Excellent for AI trust, though might benefit from engaging elements.'

            # Fallback
            else:
                score = 75
                tone = "Mixed"
                comment = f'{tone}: {positive_pct:.1f}% positive, {negative_pct:.1f}% negative, {neutral_pct:.1f}% neutral. Reasonable sentiment balance.'

            # Add compound score interpretation
            if compound_score >= 0.5:
                comment += f' Overall: strongly positive (compound: {compound_score:.2f}).'
            elif compound_score >= 0.2:
                comment += f' Overall: moderately positive (compound: {compound_score:.2f}).'
            elif compound_score >= -0.2:
                comment += f' Overall: neutral (compound: {compound_score:.2f}).'
            elif compound_score >= -0.5:
                comment += f' Overall: moderately negative (compound: {compound_score:.2f}).'
            else:
                comment += f' Overall: strongly negative (compound: {compound_score:.2f}).'

            # Recommendations based on tone
            if score < 70:
                if positive_pct > 85:
                    comment += ' Tip: Add objective data, statistics, and neutral analysis to balance promotional tone.'
                elif negative_pct > 50:
                    comment += ' Tip: Include positive aspects and constructive solutions to balance critical tone.'

            # Insight on AI model preference
            if score >= 85:
                comment += ' AI models favor this balanced, credible tone.'
            elif score >= 70:
                comment += ' Acceptable tone for AI citation.'
            else:
                comment += ' Improve tone balance for better AI model preference.'

            return {
                'score': score,
                'comment': comment
            }

        except Exception as e:
            logger.error(f"Error analyzing sentiment for {url}: {str(e)}")
            return {
                'score': 0,
                'comment': f'Sentiment analysis failed: {str(e)}'
            }


# Export for orchestrator
measurement = SentimentAnalysisMeasurement()
