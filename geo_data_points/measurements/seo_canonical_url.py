"""
SEO-002: Canonical URL Implementation

Validates canonical URL implementation to prevent duplicate content issues.
Proper canonicalization helps AI crawlers understand the preferred version of content.
"""

from typing import Dict, Any
from geo_data_points.base import BaseMeasurement
from geo_data_points.utils.html_parser import HTMLAnalyzer
from loguru import logger
from urllib.parse import urlparse, urljoin


class CanonicalURLMeasurement(BaseMeasurement):
    """Validate canonical URL implementation."""

    def __init__(self):
        super().__init__(
            code="SEO-002",
            name="Canonical URL Implementation",
            description="Validates canonical URL implementation to prevent duplicate content",
            category="SEO",
            weight=0.85  # Important for duplicate content prevention
        )

    async def measure(self, url: str, html: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Measure canonical URL implementation.

        Scoring:
        - 100: Canonical tag present, self-referencing, HTTPS, valid format
        - 90: Canonical tag present, self-referencing but HTTP
        - 80: Canonical tag present, points to different URL (intentional consolidation)
        - 60: Canonical tag present but malformed
        - 50: Canonical tag points to different domain (suspicious)
        - 0: No canonical tag (duplicate content risk)

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

            # Extract canonical URL from link rel="canonical"
            canonical_url = analyzer.get_canonical_url()

            if not canonical_url:
                # Check if this might be intentional (some pages don't need canonical)
                parsed_url = urlparse(url)

                # Homepage doesn't strictly need canonical
                if parsed_url.path in ['/', '']:
                    return {
                        'score': 80,
                        'comment': 'No canonical tag on homepage. Not critical but recommended. Add <link rel="canonical" href="https://domain.com/"> for consistency.'
                    }
                else:
                    return {
                        'score': 0,
                        'comment': 'No canonical URL tag found. CRITICAL for duplicate content prevention! Add <link rel="canonical" href="preferred-url"> to indicate preferred version. This helps AI crawlers understand which content version to index and cite.'
                    }

            # Parse canonical URL
            try:
                canonical_parsed = urlparse(canonical_url)
                current_parsed = urlparse(url)

                # Normalize URLs for comparison (remove trailing slashes, fragments)
                canonical_normalized = canonical_parsed._replace(fragment='').geturl().rstrip('/')
                current_normalized = current_parsed._replace(fragment='', query='').geturl().rstrip('/')

                # ========== CHECK 1: Self-Referencing ==========
                is_self_referencing = (canonical_normalized == current_normalized)

                # ========== CHECK 2: HTTPS ==========
                uses_https = canonical_parsed.scheme == 'https'

                # ========== CHECK 3: Same Domain ==========
                canonical_domain = canonical_parsed.netloc
                current_domain = current_parsed.netloc

                # Normalize domains (remove www)
                canonical_domain_clean = canonical_domain.replace('www.', '')
                current_domain_clean = current_domain.replace('www.', '')

                is_same_domain = (canonical_domain_clean == current_domain_clean)

                # ========== CHECK 4: Valid Format ==========
                is_absolute = canonical_parsed.scheme in ['http', 'https']

                # ========== SCORING ==========
                score = 0
                issues = []
                features = []

                if not is_absolute:
                    score = 60
                    issues.append('Canonical URL is relative (should be absolute)')
                    features.append('relative canonical')

                elif not is_same_domain:
                    score = 50
                    issues.append(f'Canonical points to different domain ({canonical_domain})')
                    features.append('cross-domain canonical')

                elif is_self_referencing:
                    # Self-referencing canonical (best practice)
                    if uses_https:
                        score = 100
                        features.append('self-referencing HTTPS canonical')
                    else:
                        score = 90
                        features.append('self-referencing HTTP canonical')
                        issues.append('Use HTTPS for canonical URL')

                else:
                    # Points to different URL on same domain
                    score = 80
                    features.append('consolidation canonical')

                    # Check if it's due to parameters
                    if current_parsed.query:
                        features.append('removes query parameters')

                    # Check if it's due to trailing slash
                    if current_normalized + '/' == canonical_normalized or canonical_normalized + '/' == current_normalized:
                        features.append('normalizes trailing slash')

                # Additional checks
                if not uses_https and is_same_domain:
                    issues.append('Canonical uses HTTP instead of HTTPS')
                    score = max(0, score - 10)

                # Check for protocol-relative URLs (bad practice)
                if canonical_url.startswith('//'):
                    issues.append('Protocol-relative URL (// format) is deprecated')
                    score = max(0, score - 10)

                # ========== GENERATE COMMENT ==========
                if score >= 95:
                    rating = "Perfect canonical implementation"
                elif score >= 85:
                    rating = "Excellent canonical implementation"
                elif score >= 70:
                    rating = "Good canonical implementation"
                elif score >= 50:
                    rating = "Problematic canonical implementation"
                else:
                    rating = "Poor canonical implementation"

                comment = f'{rating}. Canonical URL: {canonical_url}. '

                # Add features
                if features:
                    comment += f'Features: {", ".join(features)}. '

                # Add issues
                if issues:
                    comment += f'Issues: {"; ".join(issues)}. '

                # Provide context
                if is_self_referencing:
                    comment += 'Self-referencing canonical confirms this as the preferred version for AI crawlers.'
                elif is_same_domain:
                    comment += 'Canonical points to different URL - ensure this is intentional consolidation (e.g., removing URL parameters).'
                else:
                    comment += 'WARNING: Cross-domain canonical detected. Only use if intentionally syndicating content. Otherwise, this may prevent indexing.'

                # Recommendations
                if score < 90:
                    if not uses_https:
                        comment += ' Recommendation: Update canonical to HTTPS.'
                    if not is_self_referencing and is_same_domain:
                        comment += ' Verify canonical URL is intentionally different from current URL.'

                return {
                    'score': score,
                    'comment': comment
                }

            except Exception as e:
                return {
                    'score': 60,
                    'comment': f'Canonical URL found ({canonical_url}) but validation failed: {str(e)}. Ensure proper URL format.'
                }

        except Exception as e:
            logger.error(f"Error measuring canonical URL for {url}: {str(e)}")
            return {
                'score': 0,
                'comment': f'Measurement failed: {str(e)}'
            }


# Export for orchestrator
measurement = CanonicalURLMeasurement()
