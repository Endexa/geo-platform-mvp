"""
LEG-002: GDPR Compliance Signals

Checks for GDPR compliance indicators (cookie consent, data protection mentions).
GDPR compliance is mandatory for EU users and signals trustworthiness.
"""

from typing import Dict, Any
from geo_data_points.base import BaseMeasurement
from geo_data_points.utils.html_parser import HTMLAnalyzer
from loguru import logger


class GDPRComplianceMeasurement(BaseMeasurement):
    """Check GDPR compliance signals."""

    def __init__(self):
        super().__init__(
            code="LEG-002",
            name="GDPR Compliance Signals",
            description="Checks for GDPR compliance indicators (cookie consent, data protection)",
            category="Legal",
            weight=0.90  # Very high importance for EU compliance
        )

    async def measure(self, url: str, html: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Measure GDPR compliance signals.

        Scoring:
        - 100: Cookie consent banner + privacy policy + GDPR mentions
        - 85: Cookie consent + privacy policy
        - 70: Cookie consent only
        - 50: Privacy policy only (no cookie consent)
        - 25: GDPR mentions but no implementation
        - 0: No GDPR compliance signals

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

            # Check for cookie consent mechanisms
            cookie_consent_indicators = [
                'cookie consent',
                'cookie banner',
                'cookie notice',
                'accept cookies',
                'cookie policy',
                'cookies settings',
                'manage cookies',
                'reject all',
                'accept all',
                'cookie preferences',
                'onetrust',  # Common cookie consent platform
                'cookiebot',
                'cookieconsent',
                'gdpr-cookie',
                'cookie-notice'
            ]

            html_lower = html.lower()
            has_cookie_consent = any(indicator in html_lower for indicator in cookie_consent_indicators)

            # Check for privacy policy link
            all_links = analyzer.get_internal_links()
            has_privacy_policy = any(
                'privacy' in link.lower() or 'confidentialit' in link.lower()
                for link in all_links
            )

            # Check for GDPR-specific mentions
            gdpr_terms = [
                'gdpr',
                'general data protection regulation',
                'data protection',
                'data subject rights',
                'right to access',
                'right to erasure',
                'right to portability',
                'data controller',
                'data processor',
                'legitimate interest',
                'consent withdrawal',
                'rgpd'  # French acronym
            ]

            found_gdpr_terms = [term for term in gdpr_terms if term in html_lower]
            has_gdpr_mentions = len(found_gdpr_terms) > 0

            # Check for data protection officer (DPO) contact
            has_dpo_contact = 'data protection officer' in html_lower or 'dpo@' in html_lower or 'dpo ' in html_lower

            # Calculate score
            score = 0
            signals = []
            issues = []

            if has_cookie_consent:
                score += 40
                signals.append('cookie consent mechanism')
            else:
                issues.append('Missing cookie consent banner (required for GDPR)')

            if has_privacy_policy:
                score += 30
                signals.append('privacy policy')
            else:
                issues.append('Missing privacy policy link')

            if has_gdpr_mentions:
                score += 20
                gdpr_count = len(found_gdpr_terms)
                signals.append(f'GDPR mentions ({gdpr_count} terms)')
            else:
                issues.append('No GDPR-specific language found')

            if has_dpo_contact:
                score += 10
                signals.append('DPO contact info')

            # Generate comment based on score
            if score >= 90:
                comment = 'Excellent GDPR compliance! '
            elif score >= 70:
                comment = 'Good GDPR compliance signals. '
            elif score >= 50:
                comment = 'Partial GDPR compliance. '
            elif score >= 25:
                comment = 'Insufficient GDPR compliance. '
            else:
                comment = 'Critical GDPR compliance issues! '

            # Add found signals
            if signals:
                comment += f'Found: {", ".join(signals)}.'

            # Add issues
            if issues:
                comment += f' Issues: {"; ".join(issues)}.'

            # Add specific recommendations
            if not has_cookie_consent:
                comment += ' Priority: Implement cookie consent banner (OneTrust, Cookiebot, or custom solution).'
            if not has_privacy_policy:
                comment += ' Critical: Add comprehensive privacy policy with GDPR compliance details.'
            if not has_gdpr_mentions:
                comment += ' Improve: Add GDPR-specific language (data subject rights, consent management).'

            # Check for common GDPR implementation patterns
            implementation_checks = []

            # Check for cookie categories (legitimate interest, analytics, marketing)
            if 'analytics cookies' in html_lower or 'marketing cookies' in html_lower:
                implementation_checks.append('cookie categorization')
                score = min(100, score + 5)

            # Check for consent management
            if 'manage consent' in html_lower or 'cookie preferences' in html_lower:
                implementation_checks.append('consent management UI')
                score = min(100, score + 5)

            # Check for cookie declaration/list
            if 'cookie list' in html_lower or 'cookies used' in html_lower:
                implementation_checks.append('cookie declaration')

            if implementation_checks:
                comment += f' Implementation details: {", ".join(implementation_checks)}.'

            # Final compliance assessment
            if score >= 85:
                comment += ' Strong GDPR compliance posture.'
            elif score >= 70:
                comment += ' Meets basic GDPR requirements.'
            else:
                comment += ' GDPR compliance gaps detected - address immediately for EU users!'

            return {
                'score': score,
                'comment': comment
            }

        except Exception as e:
            logger.error(f"Error measuring GDPR compliance for {url}: {str(e)}")
            return {
                'score': 0,
                'comment': f'Measurement failed: {str(e)}'
            }


# Export for orchestrator
measurement = GDPRComplianceMeasurement()
