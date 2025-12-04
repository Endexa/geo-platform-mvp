"""
WI-017: Mobile Responsiveness

Checks for mobile-responsive design implementation using viewport meta tag,
media queries, and responsive design patterns.

Mobile-first indexing is standard for AI crawlers.
"""

from typing import Dict, Any
from geo_data_points.base import BaseMeasurement
from geo_data_points.utils.html_parser import HTMLAnalyzer
from loguru import logger
import re


class MobileResponsivenessMeasurement(BaseMeasurement):
    """Check mobile responsiveness implementation."""

    def __init__(self):
        super().__init__(
            code="WI-017",
            name="Mobile Responsiveness",
            description="Checks mobile-responsive design via viewport meta tag and media queries",
            category="Web Infrastructure",
            weight=0.90  # Critical for modern web and AI crawlers
        )

    async def measure(self, url: str, html: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Measure mobile responsiveness.

        Scoring:
        - 100: Viewport meta + media queries + responsive images
        - 90: Viewport meta + media queries
        - 70: Viewport meta only
        - 40: Some responsive indicators but no viewport
        - 0: No mobile responsiveness detected

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
            html_lower = html.lower()

            score = 0
            features = []
            issues = []

            # ========== 1. VIEWPORT META TAG (Essential - 40 points) ==========
            meta_tags = analyzer.get_meta_tags()
            viewport = meta_tags.get('viewport', '')

            if viewport:
                score += 40
                features.append('viewport meta tag')

                # Check for proper viewport configuration
                viewport_lower = viewport.lower()

                # Good: width=device-width
                if 'width=device-width' in viewport_lower:
                    score += 5
                    features.append('device-width')
                else:
                    issues.append('Viewport missing "width=device-width"')

                # Good: initial-scale=1
                if 'initial-scale=1' in viewport_lower:
                    score += 5
                    features.append('initial-scale=1')
                else:
                    issues.append('Consider adding "initial-scale=1" to viewport')

                # Bad: user-scalable=no (accessibility issue)
                if 'user-scalable=no' in viewport_lower or 'maximum-scale=1' in viewport_lower:
                    score -= 10
                    issues.append('Viewport disables user scaling (accessibility issue)')
                    features.append('scaling disabled (bad)')

            else:
                issues.append('CRITICAL: Missing viewport meta tag')

            # ========== 2. CSS MEDIA QUERIES (30 points) ==========
            # Check for media queries in inline styles and style tags
            media_query_patterns = [
                r'@media\s*\([^)]*(?:max-width|min-width|max-device-width|min-device-width)',
                r'@media\s+(?:screen\s+and\s+)?\([^)]*(?:max-width|min-width)',
                r'@media\s+only\s+screen'
            ]

            media_queries_found = False
            media_query_count = 0

            for pattern in media_query_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                if matches:
                    media_queries_found = True
                    media_query_count += len(matches)

            # Also check for external stylesheets (likely to have media queries)
            has_stylesheets = '<link' in html_lower and 'stylesheet' in html_lower

            if media_queries_found:
                if media_query_count >= 5:
                    score += 30
                    features.append(f'{media_query_count} media queries')
                elif media_query_count >= 2:
                    score += 25
                    features.append(f'{media_query_count} media queries')
                else:
                    score += 15
                    features.append(f'{media_query_count} media query')
            elif has_stylesheets:
                # Assume external stylesheets might have media queries
                score += 20
                features.append('external stylesheets (may contain media queries)')
            else:
                issues.append('No media queries detected')

            # ========== 3. RESPONSIVE IMAGES (15 points) ==========
            # Check for responsive image techniques
            responsive_image_features = 0

            # srcset for responsive images
            if 'srcset=' in html_lower:
                responsive_image_features += 1
                score += 5
                features.append('srcset attributes')

            # <picture> element
            if '<picture' in html_lower:
                responsive_image_features += 1
                score += 5
                features.append('picture elements')

            # sizes attribute
            if 'sizes=' in html_lower:
                responsive_image_features += 1
                score += 5
                features.append('sizes attributes')

            if responsive_image_features == 0:
                issues.append('No responsive image techniques detected')

            # ========== 4. FLEXIBLE LAYOUTS (10 points) ==========
            # Check for flexible layout indicators
            flexible_layout_features = 0

            # Flexbox
            if 'display:flex' in html_lower or 'display: flex' in html_lower:
                flexible_layout_features += 1
                score += 3
                features.append('flexbox')

            # CSS Grid
            if 'display:grid' in html_lower or 'display: grid' in html_lower:
                flexible_layout_features += 1
                score += 3
                features.append('CSS grid')

            # Relative units (%, vw, vh, em, rem)
            relative_unit_patterns = [r'\d+(?:\.\d+)?(?:vw|vh|%|em|rem)']
            uses_relative_units = any(
                re.search(pattern, html, re.IGNORECASE)
                for pattern in relative_unit_patterns
            )
            if uses_relative_units:
                flexible_layout_features += 1
                score += 4
                features.append('relative units')

            if flexible_layout_features == 0:
                issues.append('Limited flexible layout techniques')

            # Cap score at 100
            score = min(100, score)

            # ========== GENERATE COMMENT ==========
            if score >= 90:
                rating = "Excellent mobile responsiveness"
            elif score >= 70:
                rating = "Good mobile responsiveness"
            elif score >= 50:
                rating = "Basic mobile responsiveness"
            elif score >= 30:
                rating = "Limited mobile responsiveness"
            else:
                rating = "Poor mobile responsiveness"

            comment = f'{rating} (Score: {score}/100). '

            # Add features
            if features:
                comment += f'Features: {", ".join(features)}.'

            # Add issues
            if issues:
                comment += f' Issues: {"; ".join(issues)}.'

            # Critical recommendations
            if not viewport:
                comment += ' CRITICAL: Add viewport meta tag: <meta name="viewport" content="width=device-width, initial-scale=1">.'

            if not media_queries_found and not has_stylesheets:
                comment += ' Add CSS media queries for responsive breakpoints (mobile, tablet, desktop).'

            # Additional context
            if score >= 70:
                comment += ' Mobile-first indexing compatible - AI crawlers can effectively access mobile version.'
            else:
                comment += ' Improve mobile responsiveness - AI crawlers prioritize mobile-friendly sites (mobile-first indexing).'

            return {
                'score': score,
                'comment': comment
            }

        except Exception as e:
            logger.error(f"Error measuring mobile responsiveness for {url}: {str(e)}")
            return {
                'score': 0,
                'comment': f'Measurement failed: {str(e)}'
            }


# Export for orchestrator
measurement = MobileResponsivenessMeasurement()
