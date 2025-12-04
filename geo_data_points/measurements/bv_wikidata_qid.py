"""
BV-002: Wikidata QID Presence

Checks if entity has a Wikidata QID (unique identifier in Wikidata).
Wikidata presence indicates structured knowledge base recognition.
"""

from typing import Dict, Any
from geo_data_points.base import BaseMeasurement
from geo_data_points.utils.external_apis import WikidataClient
from loguru import logger


class WikidataQIDMeasurement(BaseMeasurement):
    """Check Wikidata QID presence for entity/brand."""

    def __init__(self):
        super().__init__(
            code="BV-002",
            name="Wikidata QID Presence",
            description="Checks if entity has Wikidata QID for structured knowledge recognition",
            category="Brand Visibility",
            weight=0.90  # Very high importance for entity recognition
        )
        self.wikidata_client = WikidataClient()

    async def measure(self, url: str, html: str = None, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Measure Wikidata QID presence.

        Scoring:
        - 100: Wikidata QID found with detailed entity data
        - 80: Wikidata QID found with basic data
        - 60: Wikidata QID found but minimal data
        - 0: No Wikidata QID found

        Args:
            url: Target URL to analyze
            html: Unused
            metadata: Should contain 'brand_name' or will extract from URL

        Returns:
            Dict with score (0-100) and detailed comment
        """
        try:
            # Extract brand/entity name from metadata or URL
            if metadata and 'brand_name' in metadata:
                query = metadata['brand_name']
            else:
                # Extract domain name as query
                from urllib.parse import urlparse
                parsed = urlparse(url)
                domain = parsed.netloc.replace('www.', '')
                query = domain.split('.')[0].title()

            # Search Wikidata
            qid = self.wikidata_client.find_entity_qid(query)

            if not qid:
                return {
                    'score': 0,
                    'comment': f'No Wikidata QID found for "{query}". Entity not in Wikidata knowledge base. This limits structured data recognition by AI models. Recommendation: Create Wikipedia article (which automatically generates Wikidata entry) or contribute entity data to Wikidata directly.'
                }

            # Get entity details
            entity_data = self.wikidata_client.get_entity_details(qid)

            if not entity_data:
                return {
                    'score': 60,
                    'comment': f'Wikidata QID found ({qid}) but cannot retrieve details. Basic presence confirmed.'
                }

            # Analyze entity data completeness
            label = entity_data.get('label', query)
            description = entity_data.get('description', '')
            claims_count = entity_data.get('claims_count', 0)
            aliases_count = entity_data.get('aliases_count', 0)

            # Calculate score based on data richness
            if claims_count >= 10 and description:
                score = 100
                comment = f'Excellent! Wikidata entity found: "{label}" (QID: {qid}). Rich entity data with {claims_count} claims. Perfect for AI structured knowledge!'
            elif claims_count >= 5:
                score = 90
                comment = f'Great! Wikidata entity found: "{label}" (QID: {qid}). Good entity data with {claims_count} claims. Strong AI recognition.'
            elif claims_count >= 2:
                score = 80
                comment = f'Good! Wikidata entity found: "{label}" (QID: {qid}). Basic entity data with {claims_count} claims. Add more structured data for better AI recognition.'
            else:
                score = 70
                comment = f'Wikidata entity found: "{label}" (QID: {qid}). Minimal data ({claims_count} claims). Expand entity data on Wikidata for improved AI understanding.'

            # Add description if available
            if description:
                comment += f' Description: "{description}".'

            # Add aliases info
            if aliases_count > 0:
                comment += f' {aliases_count} alternative name(s) registered.'

            # Recommendations
            if claims_count < 10:
                comment += f' Tip: Add more structured claims to Wikidata (current: {claims_count}, target: 10+).'

            return {
                'score': score,
                'comment': comment
            }

        except Exception as e:
            logger.error(f"Error checking Wikidata QID for {url}: {str(e)}")
            return {
                'score': 0,
                'comment': f'Measurement failed: {str(e)}'
            }


# Export for orchestrator
measurement = WikidataQIDMeasurement()
