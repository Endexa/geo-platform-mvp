"""
COMP-001: Domain Age

Measures domain age as a trust and authority signal.
Older domains generally have more established authority for AI models.
"""

from typing import Dict, Any
from geo_data_points.base import BaseMeasurement
from loguru import logger
from urllib.parse import urlparse
import socket
from datetime import datetime
import whois


class DomainAgeMeasurement(BaseMeasurement):
    """Measure domain age for authority signals."""

    def __init__(self):
        super().__init__(
            code="COMP-001",
            name="Domain Age",
            description="Measures domain age as trust and authority signal",
            category="Competitive",
            weight=0.70  # Moderate importance for authority
        )

    async def measure(self, url: str, html: str = None, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Measure domain age.

        Scoring:
        - 100: 10+ years (very established)
        - 90: 5-10 years (established)
        - 80: 3-5 years (mature)
        - 70: 2-3 years (developing)
        - 60: 1-2 years (young)
        - 40: 6-12 months (very young)
        - 20: <6 months (brand new)
        - 0: Cannot determine

        Args:
            url: Target URL to analyze
            html: Unused
            metadata: May contain 'domain_age' override

        Returns:
            Dict with score (0-100) and detailed comment
        """
        try:
            # Check if domain age provided in metadata
            if metadata and 'domain_age_years' in metadata:
                age_years = metadata['domain_age_years']
                return self._score_domain_age(age_years, source="metadata")

            # Extract domain
            parsed = urlparse(url)
            domain = parsed.netloc.replace('www.', '')

            try:
                # Attempt WHOIS lookup (requires python-whois)
                domain_info = whois.whois(domain)

                if domain_info and domain_info.creation_date:
                    # Handle list of dates (some registrars return multiple)
                    creation_date = domain_info.creation_date
                    if isinstance(creation_date, list):
                        creation_date = creation_date[0]

                    # Calculate age
                    now = datetime.utcnow()
                    if creation_date.tzinfo:
                        creation_date = creation_date.replace(tzinfo=None)

                    age_days = (now - creation_date).days
                    age_years = age_days / 365.25

                    # Get registrar info
                    registrar = domain_info.registrar if domain_info.registrar else "Unknown"

                    return self._score_domain_age(
                        age_years,
                        source="WHOIS",
                        creation_date=creation_date,
                        registrar=registrar
                    )

            except Exception as e:
                logger.warning(f"WHOIS lookup failed for {domain}: {str(e)}")

            # Fallback: Cannot determine domain age
            return {
                'score': 0,
                'comment': f'Cannot determine domain age for {domain}. WHOIS lookup unavailable. Domain age is a trust signal for AI models - older domains generally have more authority. Provide domain_age_years in metadata for manual scoring.'
            }

        except Exception as e:
            logger.error(f"Error measuring domain age for {url}: {str(e)}")
            return {
                'score': 0,
                'comment': f'Domain age measurement failed: {str(e)}'
            }

    def _score_domain_age(
        self,
        age_years: float,
        source: str = "",
        creation_date: datetime = None,
        registrar: str = None
    ) -> Dict[str, Any]:
        """
        Score domain age.

        Args:
            age_years: Domain age in years
            source: Data source (WHOIS, metadata, etc.)
            creation_date: Domain creation date
            registrar: Domain registrar

        Returns:
            Scoring result dict
        """
        # Calculate score based on age
        if age_years >= 10:
            score = 100
            maturity = "Very Established"
            comment = f'{maturity}: Domain is {age_years:.1f} years old. Excellent trust and authority signal for AI models!'
        elif age_years >= 5:
            score = 90
            maturity = "Established"
            comment = f'{maturity}: Domain is {age_years:.1f} years old. Strong authority signal for AI models.'
        elif age_years >= 3:
            score = 80
            maturity = "Mature"
            comment = f'{maturity}: Domain is {age_years:.1f} years old. Good trust signal.'
        elif age_years >= 2:
            score = 70
            maturity = "Developing"
            comment = f'{maturity}: Domain is {age_years:.1f} years old. Reasonable age for authority building.'
        elif age_years >= 1:
            score = 60
            maturity = "Young"
            comment = f'{maturity}: Domain is {age_years:.1f} years old. Still building authority. Focus on content quality and backlinks.'
        elif age_years >= 0.5:
            score = 40
            maturity = "Very Young"
            comment = f'{maturity}: Domain is {age_years * 12:.0f} months old. Limited trust signal. Build authority through quality content and backlinks.'
        else:
            score = 20
            maturity = "Brand New"
            comment = f'{maturity}: Domain is {age_years * 12:.0f} months old. Very limited authority signal. New domains need time to build trust with AI models.'

        # Add creation date if available
        if creation_date:
            comment += f' Created: {creation_date.strftime("%Y-%m-%d")}.'

        # Add registrar if available
        if registrar:
            comment += f' Registrar: {registrar}.'

        # Add source
        if source:
            comment += f' Source: {source}.'

        # Add context about domain age impact
        if age_years >= 5:
            comment += ' Established domain age provides strong trust signal to AI models.'
        elif age_years >= 2:
            comment += ' Moderate domain age. Continue building authority signals (backlinks, quality content).'
        else:
            comment += ' Young domain. Focus on building authority through quality content, backlinks, and consistent publishing.'

        # Recommendations
        if age_years < 2:
            comment += ' Tip: Compensate for young domain with exceptional content quality, strong backlinks, and active social presence.'

        return {
            'score': score,
            'comment': comment,
            'metadata': {
                'domain_age_years': age_years,
                'domain_age_days': int(age_years * 365.25),
                'creation_date': creation_date.isoformat() if creation_date else None,
                'registrar': registrar
            }
        }


# Export for orchestrator
measurement = DomainAgeMeasurement()
