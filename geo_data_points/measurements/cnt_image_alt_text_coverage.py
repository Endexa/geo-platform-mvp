"""
CNT-009: Image Alt Text Coverage

Measures percentage of images with descriptive alt text.
Alt text is critical for accessibility and helps AI models understand visual content.
"""

from typing import Dict, Any
from geo_data_points.base import BaseMeasurement
from geo_data_points.utils.html_parser import HTMLAnalyzer
from loguru import logger


class ImageAltTextCoverageMeasurement(BaseMeasurement):
    """Measure image alt text coverage and quality."""

    def __init__(self):
        super().__init__(
            code="CNT-009",
            name="Image Alt Text Coverage",
            description="Measures percentage of images with descriptive alt text for accessibility",
            category="Content",
            weight=0.80  # Important for accessibility and AI understanding
        )

    async def measure(self, url: str, html: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Measure image alt text coverage.

        Scoring:
        - 100: 100% images have descriptive alt text
        - 90: 90-99% coverage
        - 80: 80-89% coverage
        - 70: 70-79% coverage
        - 60: 60-69% coverage
        - 40: 40-59% coverage
        - 20: 20-39% coverage
        - 10: <20% coverage
        - 0: No images or all missing alt text

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

            # Get alt text coverage
            alt_coverage = analyzer.get_alt_text_coverage()

            if 'error' in alt_coverage:
                return {
                    'score': 0,
                    'comment': f'Alt text analysis failed: {alt_coverage["error"]}'
                }

            total_images = alt_coverage['total_images']

            if total_images == 0:
                # No images - not necessarily bad, but worth noting
                return {
                    'score': 100,
                    'comment': 'No images found on page. Alt text validation not applicable. If page should contain images, ensure they\'re properly loaded.'
                }

            images_with_alt = alt_coverage['images_with_alt']
            images_without_alt = alt_coverage['images_without_alt']
            images_with_empty_alt = alt_coverage.get('images_with_empty_alt', 0)
            coverage_percentage = alt_coverage['coverage_percentage']

            # Calculate score based on coverage
            if coverage_percentage >= 100:
                score = 100
                rating = "Perfect"
                comment = f'{rating}: All {total_images} images have alt text! Excellent accessibility and AI content understanding.'
            elif coverage_percentage >= 90:
                score = 90
                rating = "Excellent"
                comment = f'{rating}: {images_with_alt}/{total_images} images ({coverage_percentage:.1f}%) have alt text. Nearly perfect accessibility.'
            elif coverage_percentage >= 80:
                score = 80
                rating = "Good"
                comment = f'{rating}: {images_with_alt}/{total_images} images ({coverage_percentage:.1f}%) have alt text. Good accessibility, improve further.'
            elif coverage_percentage >= 70:
                score = 70
                rating = "Acceptable"
                comment = f'{rating}: {images_with_alt}/{total_images} images ({coverage_percentage:.1f}%) have alt text. Acceptable but needs improvement.'
            elif coverage_percentage >= 60:
                score = 60
                rating = "Moderate"
                comment = f'{rating}: {images_with_alt}/{total_images} images ({coverage_percentage:.1f}%) have alt text. Moderate coverage - add alt text to remaining images.'
            elif coverage_percentage >= 40:
                score = 40
                rating = "Poor"
                comment = f'{rating}: Only {images_with_alt}/{total_images} images ({coverage_percentage:.1f}%) have alt text. Poor accessibility - add alt text urgently.'
            elif coverage_percentage >= 20:
                score = 20
                rating = "Very Poor"
                comment = f'{rating}: Only {images_with_alt}/{total_images} images ({coverage_percentage:.1f}%) have alt text. Critical accessibility issue!'
            else:
                score = 10
                rating = "Critical"
                comment = f'{rating}: Only {images_with_alt}/{total_images} images ({coverage_percentage:.1f}%) have alt text. Severe accessibility violation!'

            # Check for empty alt text (decorative images)
            if images_with_empty_alt > 0:
                comment += f' {images_with_empty_alt} images have empty alt="" (decorative images).'

            # Add specific missing count
            if images_without_alt > 0:
                comment += f' {images_without_alt} images missing alt text entirely - add immediately!'

            # Alt text quality analysis (if available)
            if 'alt_text_samples' in alt_coverage and alt_coverage['alt_text_samples']:
                alt_samples = alt_coverage['alt_text_samples']

                # Check for poor quality alt text
                poor_quality = 0
                poor_indicators = ['image', 'img', 'picture', 'photo', 'icon', 'logo', 'graphic']

                for alt_text in alt_samples[:10]:  # Check first 10
                    alt_lower = alt_text.lower()
                    # Check if alt text is just generic terms
                    if any(alt_lower == indicator or alt_lower == f'{indicator}.jpg' for indicator in poor_indicators):
                        poor_quality += 1
                    # Check if alt text is too short (less than 5 chars, excluding empty)
                    elif len(alt_text) > 0 and len(alt_text) < 5:
                        poor_quality += 1

                if poor_quality > 0:
                    score = max(0, score - poor_quality * 5)  # Penalty for poor quality
                    comment += f' WARNING: {poor_quality} images have generic/poor alt text (e.g., "image", "photo"). Use descriptive alt text!'

            # Recommendations
            recommendations = []

            if coverage_percentage < 100:
                recommendations.append(f'Add alt text to {images_without_alt} remaining images')

            if coverage_percentage < 80:
                recommendations.append('Use descriptive alt text (describe what\'s in the image)')
                recommendations.append('For decorative images, use empty alt="" attribute')

            if recommendations:
                comment += f' Actions: {"; ".join(recommendations)}.'

            # Context about importance
            if score >= 90:
                comment += ' Excellent accessibility compliance - helps AI models understand visual content.'
            elif score >= 70:
                comment += ' Good progress on accessibility - continue improving alt text coverage.'
            else:
                comment += ' Critical: Alt text is required for WCAG accessibility compliance and helps AI models understand images. Add descriptive alt text to all content images.'

            return {
                'score': score,
                'comment': comment,
                'metadata': {
                    'total_images': total_images,
                    'images_with_alt': images_with_alt,
                    'images_without_alt': images_without_alt,
                    'images_with_empty_alt': images_with_empty_alt,
                    'coverage_percentage': coverage_percentage
                }
            }

        except Exception as e:
            logger.error(f"Error measuring image alt text coverage for {url}: {str(e)}")
            return {
                'score': 0,
                'comment': f'Measurement failed: {str(e)}'
            }


# Export for orchestrator
measurement = ImageAltTextCoverageMeasurement()
