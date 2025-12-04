"""
CNT-001: Entity Density

Measures the density of named entities (people, organizations, locations) in content.
High entity density indicates rich, informative content that AI models prefer.
"""

from typing import Dict, Any
from geo_data_points.base import BaseMeasurement
from geo_data_points.utils.html_parser import HTMLAnalyzer
from geo_data_points.utils.content_analyzer import ContentAnalyzer
from loguru import logger


class EntityDensityMeasurement(BaseMeasurement):
    """Measure named entity density in content."""

    def __init__(self):
        super().__init__(
            code="CNT-001",
            name="Entity Density",
            description="Measures density of named entities (people, organizations, locations) in content",
            category="Content",
            weight=0.90  # Very high importance for AI content understanding
        )

    async def measure(self, url: str, html: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Measure entity density in content.

        Scoring:
        - 100: Exceptional entity density (>8% unique entities)
        - 90: Very high density (6-8%)
        - 80: High density (4-6%)
        - 70: Good density (3-4%)
        - 60: Moderate density (2-3%)
        - 40: Low density (1-2%)
        - 20: Very low density (<1%)
        - 0: No entities found

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

            # Extract main content text
            analyzer = HTMLAnalyzer(html, url)
            main_text = analyzer.get_main_content_text()

            if not main_text or len(main_text.strip()) < 100:
                return {
                    'score': 0,
                    'comment': 'Insufficient content for entity analysis (<100 chars). Add substantive content with named entities.'
                }

            # Analyze content
            content_analyzer = ContentAnalyzer(main_text)

            # Extract entities
            entities = content_analyzer.extract_entities()

            if not entities:
                return {
                    'score': 0,
                    'comment': 'No named entities detected. Add references to people, organizations, places, or concepts to improve content richness for AI models.'
                }

            # Count unique entities
            unique_entities = len(set([e.lower() for e in entities]))

            # Count total words
            words = main_text.split()
            total_words = len(words)

            if total_words == 0:
                return {
                    'score': 0,
                    'comment': 'No content words found.'
                }

            # Calculate entity density (unique entities per 100 words)
            entity_density = (unique_entities / total_words) * 100

            # Determine score based on density
            if entity_density >= 8:
                score = 100
                comment = f'Exceptional entity density: {entity_density:.2f}% ({unique_entities} unique entities in {total_words} words). Outstanding for AI comprehension!'
            elif entity_density >= 6:
                score = 90
                comment = f'Very high entity density: {entity_density:.2f}% ({unique_entities} unique entities in {total_words} words). Excellent for AI models!'
            elif entity_density >= 4:
                score = 80
                comment = f'High entity density: {entity_density:.2f}% ({unique_entities} unique entities in {total_words} words). Great for AI understanding!'
            elif entity_density >= 3:
                score = 70
                comment = f'Good entity density: {entity_density:.2f}% ({unique_entities} unique entities in {total_words} words). Solid content for AI extraction.'
            elif entity_density >= 2:
                score = 60
                comment = f'Moderate entity density: {entity_density:.2f}% ({unique_entities} unique entities in {total_words} words). Consider adding more specific references.'
            elif entity_density >= 1:
                score = 40
                comment = f'Low entity density: {entity_density:.2f}% ({unique_entities} unique entities in {total_words} words). Add more named entities (people, orgs, places) for better AI comprehension.'
            else:
                score = 20
                comment = f'Very low entity density: {entity_density:.2f}% ({unique_entities} unique entities in {total_words} words). Content lacks specific references - add named entities for AI models.'

            # Add top entities as examples
            if unique_entities > 0:
                top_entities = list(dict.fromkeys(entities))[:5]  # First 5 unique
                comment += f' Top entities: {", ".join(top_entities)}.'

            # Recommendations
            if entity_density < 3:
                comment += ' Tip: Reference specific people, organizations, locations, or concepts relevant to your topic.'

            return {
                'score': score,
                'comment': comment
            }

        except Exception as e:
            logger.error(f"Error measuring entity density for {url}: {str(e)}")
            return {
                'score': 0,
                'comment': f'Measurement failed: {str(e)}'
            }


# Export for orchestrator
measurement = EntityDensityMeasurement()
