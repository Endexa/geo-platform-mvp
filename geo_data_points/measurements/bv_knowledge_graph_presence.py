"""
BV-001: Knowledge Graph Presence

Checks if the entity has a Google Knowledge Graph ID (kg:/m/ identifier).
KG presence is crucial for AI model entity recognition and citation preference.
"""

from typing import Dict, Any
from geo_data_points.base import BaseMeasurement
from geo_data_points.utils.external_apis import GoogleKnowledgeGraphClient
from loguru import logger


class KnowledgeGraphPresenceMeasurement(BaseMeasurement):
    """Check Google Knowledge Graph presence for entity/brand."""

    def __init__(self):
        super().__init__(
            code="BV-001",
            name="Knowledge Graph Presence",
            description="Checks if entity has Google Knowledge Graph ID for AI recognition",
            category="Brand Visibility",
            weight=1.0  # Maximum importance for entity recognition
        )
        self.kg_client = GoogleKnowledgeGraphClient()

    async def measure(self, url: str, html: str = None, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Measure Knowledge Graph presence.

        Scoring:
        - 100: KG entity found with high confidence (>0.7)
        - 80: KG entity found with medium confidence (0.5-0.7)
        - 60: KG entity found with low confidence (<0.5)
        - 0: No KG entity found

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

            # Search Knowledge Graph
            kg_result = self.kg_client.search_entity(query)

            if not kg_result:
                return {
                    'score': 0,
                    'comment': f'No Knowledge Graph entity found for "{query}". Entity not recognized by Google KG. This severely limits AI model citation preference. Recommendation: Build brand authority, get Wikipedia page, and ensure consistent NAP (Name, Address, Phone) across the web.'
                }

            # Extract KG data
            kg_mid = kg_result.get('kg_mid')
            confidence = kg_result.get('confidence', 0)
            name = kg_result.get('name', query)
            description = kg_result.get('description', '')
            types = kg_result.get('types', [])

            # Calculate score based on confidence
            if confidence >= 0.7:
                score = 100
                confidence_level = "high"
                comment = f'Excellent! Knowledge Graph entity found: "{name}" (ID: {kg_mid}). High confidence match ({confidence:.2f}). Perfect for AI model recognition!'
            elif confidence >= 0.5:
                score = 80
                confidence_level = "medium"
                comment = f'Good! Knowledge Graph entity found: "{name}" (ID: {kg_mid}). Medium confidence match ({confidence:.2f}). Improve brand consistency for higher confidence.'
            else:
                score = 60
                confidence_level = "low"
                comment = f'Knowledge Graph entity found: "{name}" (ID: {kg_mid}). Low confidence match ({confidence:.2f}). Strengthen brand signals and consistency across the web.'

            # Add entity details
            if description:
                comment += f' Description: "{description}".'

            if types:
                type_str = ", ".join(types[:3])
                comment += f' Entity types: {type_str}.'

            # Recommendations based on confidence
            if confidence < 0.7:
                comment += ' Tip: Ensure consistent brand name, get featured on authoritative sites, create Wikipedia page if eligible.'

            return {
                'score': score,
                'comment': comment
            }

        except Exception as e:
            logger.error(f"Error checking Knowledge Graph presence for {url}: {str(e)}")
            return {
                'score': 0,
                'comment': f'Measurement failed: {str(e)}. Ensure Google Knowledge Graph API is configured.'
            }


# Export for orchestrator
measurement = KnowledgeGraphPresenceMeasurement()
