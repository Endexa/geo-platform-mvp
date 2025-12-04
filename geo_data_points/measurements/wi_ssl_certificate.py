"""
WI-016: SSL Certificate Validation

Validates SSL/TLS certificate status, expiration, and security configuration.
HTTPS is required for AI crawler trust and content credibility.
"""

from typing import Dict, Any
from geo_data_points.base import BaseMeasurement
from geo_data_points.utils.seo_helpers import check_ssl_certificate
from loguru import logger
from datetime import datetime
from urllib.parse import urlparse


class SSLCertificateMeasurement(BaseMeasurement):
    """Validate SSL certificate configuration and security."""

    def __init__(self):
        super().__init__(
            code="WI-016",
            name="SSL Certificate Validation",
            description="Validates SSL/TLS certificate status, expiration, and security configuration",
            category="Web Infrastructure",
            weight=0.95  # Critical for trust and security
        )

    async def measure(self, url: str, html: str = None, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Measure SSL certificate validity and configuration.

        Scoring:
        - 100: Valid certificate, >90 days until expiration, strong cipher
        - 90: Valid certificate, 30-90 days until expiration
        - 70: Valid certificate, <30 days until expiration (renewal urgent)
        - 50: Valid certificate but weak configuration
        - 0: No HTTPS, expired certificate, or invalid certificate

        Args:
            url: Target URL to analyze
            html: Unused (certificate checked via socket)
            metadata: Unused

        Returns:
            Dict with score (0-100) and detailed comment
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.replace('www.', '')

            # Check if URL uses HTTPS
            if parsed.scheme != 'https':
                return {
                    'score': 0,
                    'comment': f'Site uses HTTP instead of HTTPS. CRITICAL SECURITY ISSUE! AI crawlers and users will not trust your content. Implement HTTPS immediately with Let\'s Encrypt (free) or commercial SSL certificate. This is mandatory for modern web security.'
                }

            # Check SSL certificate
            ssl_info = check_ssl_certificate(domain)

            if not ssl_info or 'error' in ssl_info:
                error_msg = ssl_info.get('error', 'Unknown error') if ssl_info else 'Certificate check failed'
                return {
                    'score': 0,
                    'comment': f'SSL certificate validation failed: {error_msg}. Ensure valid certificate is properly installed. AI crawlers cannot access sites with invalid certificates.'
                }

            # Extract certificate details
            is_valid = ssl_info.get('valid', False)
            days_until_expiry = ssl_info.get('days_until_expiry', 0)
            issuer = ssl_info.get('issuer', 'Unknown')
            subject = ssl_info.get('subject', 'Unknown')
            expires_on = ssl_info.get('expires_on', 'Unknown')
            version = ssl_info.get('version', 'Unknown')

            if not is_valid:
                reason = ssl_info.get('validation_error', 'Certificate invalid')
                return {
                    'score': 0,
                    'comment': f'SSL certificate INVALID: {reason}. AI crawlers will not access site with invalid certificates. Fix certificate issues immediately!'
                }

            # Check expiration status
            if days_until_expiry < 0:
                return {
                    'score': 0,
                    'comment': f'SSL certificate EXPIRED ({abs(days_until_expiry)} days ago). CRITICAL! Site is insecure and inaccessible to AI crawlers. Renew certificate immediately!'
                }
            elif days_until_expiry < 7:
                score = 60
                urgency = "EXTREMELY URGENT"
                comment = f'{urgency}: SSL certificate expires in {days_until_expiry} days! Renew immediately to prevent site downtime and loss of AI crawler access.'
            elif days_until_expiry < 30:
                score = 70
                urgency = "URGENT"
                comment = f'{urgency}: SSL certificate expires in {days_until_expiry} days. Schedule renewal soon to avoid disruption.'
            elif days_until_expiry < 90:
                score = 90
                urgency = "Good"
                comment = f'{urgency}: SSL certificate expires in {days_until_expiry} days. Plan renewal within 30 days for best practices.'
            else:
                score = 100
                urgency = "Excellent"
                comment = f'{urgency}: SSL certificate valid for {days_until_expiry} days. Strong security posture for AI crawler trust.'

            # Add certificate details
            comment += f' Issuer: {issuer}. Subject: {subject}. Expires: {expires_on}.'

            # Check for strong cipher suites
            cipher_suite = ssl_info.get('cipher_suite', '')
            if cipher_suite:
                # Check for weak ciphers (MD5, DES, RC4, etc.)
                weak_indicators = ['md5', 'des', 'rc4', 'export', 'null']
                is_weak = any(indicator in cipher_suite.lower() for indicator in weak_indicators)

                if is_weak:
                    score = max(0, score - 30)
                    comment += f' WARNING: Weak cipher suite detected ({cipher_suite}). Upgrade to modern TLS 1.3 with strong ciphers.'
                else:
                    # Check for strong modern ciphers
                    strong_indicators = ['aes256', 'gcm', 'sha256', 'ecdhe']
                    is_strong = any(indicator in cipher_suite.lower() for indicator in strong_indicators)

                    if is_strong:
                        comment += f' Strong cipher suite: {cipher_suite}.'
                    else:
                        comment += f' Cipher suite: {cipher_suite}.'

            # Check TLS version
            tls_version = ssl_info.get('tls_version', '')
            if tls_version:
                if 'TLSv1.3' in tls_version or 'TLS 1.3' in tls_version:
                    comment += ' TLS 1.3 supported (excellent).'
                elif 'TLSv1.2' in tls_version or 'TLS 1.2' in tls_version:
                    comment += ' TLS 1.2 supported (good).'
                elif 'TLSv1.1' in tls_version or 'TLSv1.0' in tls_version or 'TLS 1.1' in tls_version or 'TLS 1.0' in tls_version:
                    score = max(0, score - 20)
                    comment += f' WARNING: Outdated TLS version ({tls_version}). Upgrade to TLS 1.2 or 1.3.'
                elif 'SSLv' in tls_version:
                    score = max(0, score - 40)
                    comment += f' CRITICAL: Insecure SSL version ({tls_version}). Disable SSL and use TLS 1.2+ only!'

            # Check for common CA (Certificate Authority)
            trusted_cas = [
                "Let's Encrypt",
                "DigiCert",
                "Comodo",
                "GeoTrust",
                "GlobalSign",
                "Sectigo",
                "Amazon",
                "Google Trust Services",
                "CloudFlare"
            ]

            is_trusted_ca = any(ca.lower() in issuer.lower() for ca in trusted_cas)
            if is_trusted_ca:
                comment += ' Trusted CA.'
            else:
                # Not necessarily bad, but worth noting
                comment += f' CA: {issuer}.'

            # Recommendations based on score
            if score < 70:
                comment += ' Recommendation: Renew certificate and ensure TLS 1.2+ with strong ciphers (AES-256-GCM).'
            elif score < 90:
                comment += ' Recommendation: Plan certificate renewal and review security configuration.'

            return {
                'score': score,
                'comment': comment
            }

        except Exception as e:
            logger.error(f"Error validating SSL certificate for {url}: {str(e)}")
            return {
                'score': 0,
                'comment': f'SSL validation failed: {str(e)}. Ensure site is accessible via HTTPS.'
            }


# Export for orchestrator
measurement = SSLCertificateMeasurement()
