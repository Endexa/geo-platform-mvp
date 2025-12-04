"""
WI-018: Meta Description Optimization

Validates meta description presence, length, and quality.
Meta descriptions influence click-through rates and help AI models understand page content.
"""

from typing import Dict, Any
from geo_data_points.base import BaseMeasurement
from geo_data_points.utils.html_parser import HTMLAnalyzer
from loguru import logger


class MetaDescriptionMeasurement(BaseMeasurement):
    """Validate meta description optimization."""

    def __init__(self):
        super().__init__(
            code="WI-018",
            name="Meta Description Optimization",
            description="Validates meta description presence, length, and quality",
            category="Web Infrastructure",
            weight=0.85  # Important for SERP appearance and AI understanding
        )

    async def measure(self, url: str, html: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Measure meta description quality.

        Scoring:
        - 100: Meta description present, optimal length (140-160 chars), unique, compelling
        - 90: Present, good length (120-160 chars), descriptive
        - 80: Present, acceptable length (100-160 chars)
        - 70: Present but too short (<100 chars) or slightly too long (160-180 chars)
        - 50: Present but too long (>180 chars) or very short (<50 chars)
        - 30: Present but duplicate/generic
        - 0: Missing meta description

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

            analyzer = HTMLAnalyzer(html, url)
            meta_tags = analyzer.get_meta_tags()

            # Get meta description
            meta_description = meta_tags.get('description', '')

            if not meta_description:
                return {
                    'score': 0,
                    'comment': 'No meta description found. CRITICAL for SERP appearance and AI content understanding! Add <meta name="description" content="compelling 140-160 character summary"> to head section. This significantly impacts click-through rates and helps AI models understand page content.'
                }

            # Analyze description
            desc_length = len(meta_description)
            desc_words = meta_description.split()
            word_count = len(desc_words)

            # Check for common issues
            issues = []
            features = []

            # ========== LENGTH ANALYSIS ==========
            if 140 <= desc_length <= 160:
                length_score = 100
                features.append(f'optimal length ({desc_length} chars)')
            elif 120 <= desc_length < 140:
                length_score = 95
                features.append(f'good length ({desc_length} chars)')
            elif 100 <= desc_length < 120:
                length_score = 85
                features.append(f'acceptable length ({desc_length} chars)')
            elif 160 < desc_length <= 180:
                length_score = 75
                issues.append(f'slightly too long ({desc_length} chars, may be truncated in SERPs)')
            elif desc_length < 100:
                length_score = 70
                issues.append(f'too short ({desc_length} chars, aim for 140-160)')
            elif desc_length > 180:
                length_score = 50
                issues.append(f'too long ({desc_length} chars, will be truncated)')
            else:
                length_score = 60

            # ========== CONTENT QUALITY ANALYSIS ==========
            quality_score = 100

            # Check for generic/template content
            generic_patterns = [
                'lorem ipsum',
                'default description',
                'this is a page',
                'welcome to',
                'enter site description',
                'add description here'
            ]

            desc_lower = meta_description.lower()
            is_generic = any(pattern in desc_lower for pattern in generic_patterns)

            if is_generic:
                quality_score -= 40
                issues.append('generic/template description detected')

            # Check for duplicate title in description
            title_tag = meta_tags.get('title', '')
            if title_tag and title_tag.lower() == meta_description.lower():
                quality_score -= 30
                issues.append('description identical to title (should be complementary)')

            # Check if description is just keywords (low word variety)
            if word_count > 0:
                unique_words = len(set([w.lower() for w in desc_words]))
                word_variety_ratio = unique_words / word_count

                if word_variety_ratio < 0.6:  # Less than 60% unique words
                    quality_score -= 20
                    issues.append('low word variety (possible keyword stuffing)')

            # Check for sentence structure
            has_period = '.' in meta_description
            has_question = '?' in meta_description
            has_exclamation = '!' in meta_description
            has_punctuation = has_period or has_question or has_exclamation

            if not has_punctuation and desc_length > 50:
                quality_score -= 10
                issues.append('no punctuation (may lack proper sentence structure)')

            # Check if starts with capital letter
            if meta_description and not meta_description[0].isupper():
                quality_score -= 5
                issues.append('should start with capital letter')

            # Check for call-to-action (positive signal)
            cta_indicators = [
                'learn', 'discover', 'find', 'explore', 'get', 'try',
                'read', 'see', 'watch', 'download', 'start', 'join'
            ]

            has_cta = any(indicator in desc_lower for indicator in cta_indicators)
            if has_cta:
                quality_score += 5
                features.append('includes call-to-action')

            # Check for numbers/statistics (engaging)
            import re
            has_numbers = bool(re.search(r'\d+', meta_description))
            if has_numbers:
                quality_score += 5
                features.append('includes numbers/statistics')

            # ========== CALCULATE FINAL SCORE ==========
            # Weight: length 60%, quality 40%
            final_score = int(length_score * 0.6 + quality_score * 0.4)
            final_score = max(0, min(100, final_score))

            # ========== GENERATE COMMENT ==========
            if final_score >= 90:
                rating = "Excellent meta description"
            elif final_score >= 80:
                rating = "Good meta description"
            elif final_score >= 70:
                rating = "Acceptable meta description"
            elif final_score >= 50:
                rating = "Poor meta description"
            else:
                rating = "Very poor meta description"

            comment = f'{rating}. Length: {desc_length} characters, {word_count} words.'

            # Add description preview
            if desc_length <= 60:
                comment += f' Content: "{meta_description}"'
            else:
                comment += f' Preview: "{meta_description[:60]}..."'

            # Add features
            if features:
                comment += f' Features: {", ".join(features)}.'

            # Add issues
            if issues:
                comment += f' Issues: {"; ".join(issues)}.'

            # ========== RECOMMENDATIONS ==========
            recommendations = []

            if desc_length < 140:
                recommendations.append(f'Expand to 140-160 characters (add {140 - desc_length} chars)')
            elif desc_length > 160:
                recommendations.append(f'Shorten to 140-160 characters (remove {desc_length - 160} chars)')

            if not has_cta and desc_length < 150:
                recommendations.append('Add call-to-action (learn, discover, get)')

            if not has_numbers and desc_length < 150:
                recommendations.append('Consider adding numbers/statistics for engagement')

            if is_generic:
                recommendations.append('Write unique, compelling description specific to page content')

            if recommendations:
                comment += f' Recommendations: {"; ".join(recommendations[:2])}.'

            # Add AI/SEO context
            if final_score >= 85:
                comment += ' Strong meta description for both SERP CTR and AI content understanding.'
            elif final_score >= 70:
                comment += ' Acceptable for SERP appearance, but can be improved for better CTR.'
            else:
                comment += ' Improve meta description - critical for SERP CTR and AI model understanding of page purpose.'

            return {
                'score': final_score,
                'comment': comment,
                'metadata': {
                    'length': desc_length,
                    'word_count': word_count,
                    'has_cta': has_cta,
                    'has_numbers': has_numbers,
                    'content': meta_description
                }
            }

        except Exception as e:
            logger.error(f"Error measuring meta description for {url}: {str(e)}")
            return {
                'score': 0,
                'comment': f'Measurement failed: {str(e)}'
            }


# Export for orchestrator
measurement = MetaDescriptionMeasurement()
