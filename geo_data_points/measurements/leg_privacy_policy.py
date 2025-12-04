"""
LEG-001: Privacy Policy Presence

Checks for privacy policy presence and accessibility.
Privacy policies are required for GDPR/CCPA compliance and user trust.
"""

from typing import Dict, Any
from geo_data_points.base import BaseMeasurement
from geo_data_points.utils.http_client import CachedSession
from geo_data_points.utils.html_parser import HTMLAnalyzer
from loguru import logger


class PrivacyPolicyMeasurement(BaseMeasurement):
    """Check privacy policy presence and quality."""

    def __init__(self):
        super().__init__(
            code="LEG-001",
            name="Privacy Policy Presence",
            description="Checks for privacy policy presence and accessibility",
            category="Legal",
            weight=0.85  # High importance for compliance and trust
        )
        self.session = CachedSession()

    async def measure(self, url: str, html: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Measure privacy policy presence.

        Scoring:
        - 100: Privacy policy found, accessible, substantial content (>500 words)
        - 80: Privacy policy found, accessible, moderate content (200-500 words)
        - 60: Privacy policy found but minimal content (<200 words)
        - 40: Privacy policy link found but page inaccessible
        - 0: No privacy policy found

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

            # Look for privacy policy links
            all_links = analyzer.get_internal_links()

            privacy_keywords = [
                'privacy',
                'confidentialit',  # French
                'datenschutz',  # German
                'privacidad',  # Spanish
                'privacy-policy',
                'politique-confidentialite'
            ]

            privacy_links = []
            for link in all_links:
                link_lower = link.lower()
                if any(keyword in link_lower for keyword in privacy_keywords):
                    privacy_links.append(link)

            if not privacy_links:
                # Check footer/header text for privacy mentions
                footer = analyzer.get_footer_text()
                header = analyzer.get_header_text()

                has_privacy_mention = any(
                    keyword in footer.lower() or keyword in header.lower()
                    for keyword in privacy_keywords[:3]
                )

                if has_privacy_mention:
                    return {
                        'score': 20,
                        'comment': 'Privacy policy mentioned but no accessible link found. Add clear privacy policy link in footer. Required for GDPR/CCPA compliance and user trust.'
                    }
                else:
                    return {
                        'score': 0,
                        'comment': 'No privacy policy found. Critical compliance issue! Add comprehensive privacy policy immediately. Required by GDPR, CCPA, and essential for user trust and AI model credibility assessment.'
                    }

            # Found privacy policy link(s) - check accessibility
            privacy_url = privacy_links[0]  # Use first found

            # Make privacy URL absolute
            from urllib.parse import urljoin, urlparse
            privacy_url_full = urljoin(url, privacy_url)

            try:
                # Fetch privacy policy page
                response = self.session.get(privacy_url_full, timeout=10)

                if response.status_code != 200:
                    return {
                        'score': 40,
                        'comment': f'Privacy policy link found ({privacy_url}) but page inaccessible (HTTP {response.status_code}). Fix broken link immediately for compliance!'
                    }

                # Analyze privacy policy content
                privacy_html = response.text
                privacy_analyzer = HTMLAnalyzer(privacy_html, privacy_url_full)
                privacy_text = privacy_analyzer.get_main_content_text()

                word_count = len(privacy_text.split())

                if word_count < 50:
                    return {
                        'score': 30,
                        'comment': f'Privacy policy found but inadequate content ({word_count} words). Add comprehensive privacy policy covering data collection, usage, storage, rights. Required for GDPR/CCPA!'
                    }
                elif word_count < 200:
                    score = 60
                    comment = f'Privacy policy found with minimal content ({word_count} words). Expand to cover all required elements: data collection, usage, third parties, user rights, contact info.'
                elif word_count < 500:
                    score = 80
                    comment = f'Privacy policy found with moderate content ({word_count} words). Good foundation - ensure coverage of GDPR/CCPA requirements.'
                else:
                    score = 100
                    comment = f'Excellent! Comprehensive privacy policy found ({word_count} words). Strong compliance and trust signal.'

                # Check for key compliance terms
                compliance_terms = [
                    'gdpr', 'general data protection regulation',
                    'ccpa', 'california consumer privacy',
                    'personal data', 'data protection',
                    'cookie', 'consent',
                    'data subject rights', 'right to access'
                ]

                privacy_text_lower = privacy_text.lower()
                found_terms = [term for term in compliance_terms if term in privacy_text_lower]

                if len(found_terms) >= 3:
                    comment += f' Contains key compliance terms: {", ".join(found_terms[:3])}.'
                elif len(found_terms) > 0:
                    comment += f' Mentions: {", ".join(found_terms)}. Add more compliance-specific language.'
                else:
                    score = max(0, score - 20)
                    comment += ' Warning: Missing key compliance terms (GDPR, CCPA, consent). Update policy!'

                # Check last update date
                if 'last updated' in privacy_text_lower or 'effective date' in privacy_text_lower:
                    comment += ' Last update date found (good practice).'
                else:
                    comment += ' Tip: Add "Last Updated" date to policy.'

                return {
                    'score': score,
                    'comment': comment
                }

            except Exception as e:
                return {
                    'score': 40,
                    'comment': f'Privacy policy link found but cannot access: {str(e)}. Ensure policy page is publicly accessible.'
                }

        except Exception as e:
            logger.error(f"Error measuring privacy policy for {url}: {str(e)}")
            return {
                'score': 0,
                'comment': f'Measurement failed: {str(e)}'
            }


# Export for orchestrator
measurement = PrivacyPolicyMeasurement()
