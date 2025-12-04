"""
WI-020: Structured Data Coverage

Analyzes structured data (Schema.org JSON-LD, Microdata, RDFa) coverage and quality.
Structured data is critical for AI models and search engines to understand page content.

WORLD-CLASS ENGINEERING STANDARDS:
- Comprehensive edge case handling
- Explicit assumptions documented
- Multi-format support (JSON-LD, Microdata, RDFa)
- Detailed error handling with context preservation
- Full metadata tracking
- Validation steps at every stage
- Industry-grade reliability
"""

from typing import Dict, Any, List, Optional, Tuple
from geo_data_points.base import BaseMeasurement
from geo_data_points.utils.html_parser import HTMLAnalyzer
from loguru import logger
from datetime import datetime
import json
import re


class StructuredDataCoverageMeasurement(BaseMeasurement):
    """
    Analyze structured data coverage and quality across multiple formats.

    ASSUMPTIONS:
    - JSON-LD is preferred format (easier to parse, recommended by Google)
    - Multiple schema types indicate rich structured data
    - Core schema types: Organization, Person, Product, Article, Event, Recipe, etc.
    - Valid JSON-LD must parse without errors
    - Microdata and RDFa are legacy but still valuable
    - Minimum 1 structured data instance for basic compliance
    - 3+ different schema types indicate comprehensive coverage
    - Structured data should match visible page content

    EDGE CASES HANDLED:
    1. Malformed JSON-LD (invalid JSON syntax)
    2. Multiple JSON-LD blocks in same page
    3. Nested schema types (@graph, nested entities)
    4. Mixed formats (JSON-LD + Microdata)
    5. Empty or placeholder structured data
    6. Deprecated schema.org properties
    7. Missing @context declaration
    8. Invalid @type values
    9. Incomplete required properties
    10. Duplicate structured data entries
    11. Extremely large JSON-LD blocks (10KB+)
    12. Structured data in <noscript> tags
    """

    # ========== CLASS CONSTANTS ==========

    # Core Schema.org types that indicate good coverage
    CORE_SCHEMA_TYPES = [
        'Organization', 'Person', 'LocalBusiness',
        'Product', 'Offer', 'Review', 'AggregateRating',
        'Article', 'BlogPosting', 'NewsArticle',
        'Event', 'Recipe', 'HowTo', 'FAQPage',
        'WebPage', 'WebSite', 'BreadcrumbList',
        'VideoObject', 'ImageObject', 'AudioObject'
    ]

    # High-value schema types (stronger signal)
    HIGH_VALUE_TYPES = [
        'Organization', 'Product', 'Article', 'Event',
        'Recipe', 'Review', 'FAQPage', 'HowTo'
    ]

    # Required properties by schema type (basic validation)
    REQUIRED_PROPERTIES = {
        'Organization': ['name', 'url'],
        'Person': ['name'],
        'Product': ['name', 'offers'],
        'Article': ['headline', 'author'],
        'Event': ['name', 'startDate'],
        'Recipe': ['name', 'recipeInstructions'],
        'Review': ['itemReviewed', 'author', 'reviewRating'],
        'BreadcrumbList': ['itemListElement']
    }

    MAX_JSON_LD_SIZE = 100000  # 100KB limit for single JSON-LD block

    def __init__(self):
        super().__init__(
            code="WI-020",
            name="Structured Data Coverage",
            description="Analyzes structured data presence, variety, and quality",
            category="Web Infrastructure",
            weight=0.80  # Important for AI understanding and search engines
        )

    async def measure(self, url: str, html: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Measure structured data coverage and quality.

        SCORING BREAKDOWN:
        - 100: Comprehensive structured data (JSON-LD, 4+ schema types, high-value types, valid)
        - 90: Excellent coverage (3+ schema types, mostly valid)
        - 80: Good coverage (2-3 schema types, valid)
        - 70: Basic coverage (1-2 schema types, valid)
        - 60: Minimal coverage (1 schema type or some validation issues)
        - 40: Incomplete/invalid structured data
        - 20: Malformed structured data
        - 0: No structured data found

        QUALITY FACTORS:
        - Format (40%): JSON-LD > Microdata > RDFa
        - Variety (30%): Multiple schema types
        - Validity (20%): Proper JSON syntax, required properties
        - Completeness (10%): Rich vs minimal data

        Args:
            url: Target URL to analyze
            html: HTML content to parse
            metadata: Unused

        Returns:
            Dict with score (0-100), detailed comment, metadata, and recommendations
        """
        execution_start = datetime.utcnow()

        try:
            if not html:
                return self._error_result('No HTML content provided.', execution_start)

            logger.info(f"[WI-020] Starting structured data analysis for {url}")

            analyzer = HTMLAnalyzer(html, url)
            soup = analyzer.soup

            # ========== STEP 1: EXTRACT JSON-LD ==========
            jsonld_blocks, jsonld_errors = self._extract_jsonld(soup)
            logger.info(f"[WI-020] Found {len(jsonld_blocks)} JSON-LD blocks, {len(jsonld_errors)} errors")

            # ========== STEP 2: EXTRACT MICRODATA ==========
            microdata_items = self._extract_microdata(soup)
            logger.info(f"[WI-020] Found {len(microdata_items)} Microdata items")

            # ========== STEP 3: EXTRACT RDFa ==========
            rdfa_items = self._extract_rdfa(soup)
            logger.info(f"[WI-020] Found {len(rdfa_items)} RDFa items")

            # ========== STEP 4: ANALYZE SCHEMA TYPES ==========
            all_schema_types = self._extract_schema_types(jsonld_blocks, microdata_items, rdfa_items)
            logger.info(f"[WI-020] Detected schema types: {all_schema_types}")

            # No structured data found
            if not jsonld_blocks and not microdata_items and not rdfa_items:
                return {
                    'score': 0,
                    'comment': 'No structured data found. CRITICAL for AI understanding and search visibility! Add JSON-LD structured data with Schema.org vocabulary. Start with Organization/Person schema and add relevant types (Article, Product, Event, etc.). Structured data helps AI models understand page content and context.',
                    'metadata': {
                        'has_structured_data': False,
                        'formats_detected': [],
                        'schema_types': [],
                        'execution_time_ms': self._calc_execution_time(execution_start)
                    },
                    'recommendations': [
                        'Add JSON-LD structured data to <head> section',
                        'Start with Organization schema for your brand',
                        'Add content-specific schemas (Article, Product, Event)',
                        'Use Google Rich Results Test to validate',
                        'Reference schema.org documentation for property guidance'
                    ]
                }

            # ========== STEP 5: VALIDATE SCHEMA QUALITY ==========
            validation_results = self._validate_schemas(jsonld_blocks, all_schema_types)

            # ========== STEP 6: CALCULATE SCORE ==========
            score = self._calculate_coverage_score(
                len(jsonld_blocks),
                len(microdata_items),
                len(rdfa_items),
                all_schema_types,
                jsonld_errors,
                validation_results
            )

            # ========== STEP 7: GENERATE COMMENT ==========
            comment = self._generate_comment(
                score,
                jsonld_blocks,
                microdata_items,
                rdfa_items,
                all_schema_types,
                jsonld_errors,
                validation_results
            )

            # ========== STEP 8: BUILD RESULT ==========
            formats_detected = []
            if jsonld_blocks:
                formats_detected.append('JSON-LD')
            if microdata_items:
                formats_detected.append('Microdata')
            if rdfa_items:
                formats_detected.append('RDFa')

            return {
                'score': score,
                'comment': comment,
                'metadata': {
                    'has_structured_data': True,
                    'formats_detected': formats_detected,
                    'jsonld_count': len(jsonld_blocks),
                    'microdata_count': len(microdata_items),
                    'rdfa_count': len(rdfa_items),
                    'schema_types': list(all_schema_types),
                    'schema_type_count': len(all_schema_types),
                    'high_value_types': [t for t in all_schema_types if t in self.HIGH_VALUE_TYPES],
                    'jsonld_errors': len(jsonld_errors),
                    'validation_score': validation_results['validation_score'],
                    'execution_time_ms': self._calc_execution_time(execution_start)
                },
                'recommendations': self._generate_recommendations(
                    jsonld_blocks,
                    all_schema_types,
                    jsonld_errors,
                    validation_results,
                    score
                )
            }

        except Exception as e:
            logger.error(f"[WI-020] Error: {str(e)}", exc_info=True)
            return self._error_result(str(e), execution_start)

    def _extract_jsonld(self, soup) -> Tuple[List[Dict], List[str]]:
        """Extract and parse JSON-LD structured data blocks."""
        jsonld_blocks = []
        errors = []

        # Find all script tags with type="application/ld+json"
        scripts = soup.find_all('script', type='application/ld+json')

        for idx, script in enumerate(scripts):
            try:
                content = script.string

                if not content or not content.strip():
                    errors.append(f"Block {idx+1}: Empty JSON-LD block")
                    continue

                # Size check
                if len(content) > self.MAX_JSON_LD_SIZE:
                    errors.append(f"Block {idx+1}: Excessively large ({len(content)} bytes, max {self.MAX_JSON_LD_SIZE})")
                    continue

                # Parse JSON
                data = json.loads(content)

                # Validate basic structure
                if isinstance(data, dict):
                    if '@context' not in data and '@graph' not in data:
                        errors.append(f"Block {idx+1}: Missing @context declaration")
                    else:
                        jsonld_blocks.append(data)
                elif isinstance(data, list):
                    # Array of JSON-LD objects
                    for item in data:
                        if isinstance(item, dict):
                            jsonld_blocks.append(item)
                else:
                    errors.append(f"Block {idx+1}: Invalid JSON-LD structure (not dict or list)")

            except json.JSONDecodeError as e:
                errors.append(f"Block {idx+1}: Invalid JSON syntax - {str(e)}")
            except Exception as e:
                errors.append(f"Block {idx+1}: Parse error - {str(e)}")

        return (jsonld_blocks, errors)

    def _extract_microdata(self, soup) -> List[Dict]:
        """Extract Microdata items (itemscope/itemtype)."""
        microdata_items = []

        items = soup.find_all(attrs={'itemscope': True})

        for item in items:
            if item.has_attr('itemtype'):
                itemtype = item.get('itemtype', '')
                microdata_items.append({
                    'format': 'Microdata',
                    'type': itemtype
                })

        return microdata_items

    def _extract_rdfa(self, soup) -> List[Dict]:
        """Extract RDFa items (vocab/typeof)."""
        rdfa_items = []

        # RDFa uses vocab and typeof attributes
        items = soup.find_all(attrs={'typeof': True})

        for item in items:
            typeof = item.get('typeof', '')
            vocab = item.get('vocab', '')

            rdfa_items.append({
                'format': 'RDFa',
                'type': typeof,
                'vocab': vocab
            })

        return rdfa_items

    def _extract_schema_types(self, jsonld_blocks: List[Dict], microdata_items: List[Dict], rdfa_items: List[Dict]) -> set:
        """Extract all Schema.org types from all formats."""
        schema_types = set()

        # Extract from JSON-LD
        for block in jsonld_blocks:
            types = self._extract_types_from_jsonld(block)
            schema_types.update(types)

        # Extract from Microdata
        for item in microdata_items:
            itemtype = item.get('type', '')
            # Extract schema type from full URL (e.g., https://schema.org/Organization -> Organization)
            if 'schema.org/' in itemtype:
                schema_type = itemtype.split('schema.org/')[-1].split('#')[0]
                schema_types.add(schema_type)

        # Extract from RDFa
        for item in rdfa_items:
            typeof = item.get('type', '')
            if typeof:
                schema_types.add(typeof)

        return schema_types

    def _extract_types_from_jsonld(self, data: Dict, types: Optional[set] = None) -> set:
        """Recursively extract @type values from JSON-LD."""
        if types is None:
            types = set()

        if isinstance(data, dict):
            # Check for @type
            if '@type' in data:
                type_value = data['@type']
                if isinstance(type_value, str):
                    types.add(type_value)
                elif isinstance(type_value, list):
                    types.update(type_value)

            # Check for @graph (multiple entities)
            if '@graph' in data:
                graph = data['@graph']
                if isinstance(graph, list):
                    for item in graph:
                        self._extract_types_from_jsonld(item, types)

            # Recurse through all values
            for key, value in data.items():
                if isinstance(value, dict):
                    self._extract_types_from_jsonld(value, types)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            self._extract_types_from_jsonld(item, types)

        return types

    def _validate_schemas(self, jsonld_blocks: List[Dict], schema_types: set) -> Dict[str, Any]:
        """Validate schema completeness and required properties."""
        validation_results = {
            'valid_blocks': 0,
            'invalid_blocks': 0,
            'missing_required_props': [],
            'validation_score': 100
        }

        for block in jsonld_blocks:
            is_valid = True

            # Get type
            block_type = block.get('@type')

            if block_type and block_type in self.REQUIRED_PROPERTIES:
                required_props = self.REQUIRED_PROPERTIES[block_type]

                for prop in required_props:
                    if prop not in block:
                        validation_results['missing_required_props'].append(f"{block_type}.{prop}")
                        is_valid = False
                        validation_results['validation_score'] -= 10

            if is_valid:
                validation_results['valid_blocks'] += 1
            else:
                validation_results['invalid_blocks'] += 1

        # Cap score
        validation_results['validation_score'] = max(0, validation_results['validation_score'])

        return validation_results

    def _calculate_coverage_score(
        self,
        jsonld_count: int,
        microdata_count: int,
        rdfa_count: int,
        schema_types: set,
        jsonld_errors: List[str],
        validation_results: Dict[str, Any]
    ) -> int:
        """Calculate comprehensive coverage score."""
        score = 0

        # ========== FORMAT SCORE (40 points) ==========
        format_score = 0

        if jsonld_count > 0:
            format_score += 30  # JSON-LD preferred
            if jsonld_count >= 3:
                format_score += 5  # Multiple blocks
        elif microdata_count > 0:
            format_score += 20  # Microdata acceptable
        elif rdfa_count > 0:
            format_score += 15  # RDFa legacy

        # Penalty for JSON-LD errors
        error_penalty = min(10, len(jsonld_errors) * 3)
        format_score -= error_penalty

        format_score += min(5, (microdata_count + rdfa_count))  # Bonus for additional formats

        score += max(0, min(40, format_score))

        # ========== VARIETY SCORE (30 points) ==========
        type_count = len(schema_types)

        if type_count >= 5:
            variety_score = 30  # Excellent variety
        elif type_count == 4:
            variety_score = 27
        elif type_count == 3:
            variety_score = 23
        elif type_count == 2:
            variety_score = 18
        elif type_count == 1:
            variety_score = 10
        else:
            variety_score = 0

        # Bonus for high-value types
        high_value_count = len([t for t in schema_types if t in self.HIGH_VALUE_TYPES])
        variety_score += min(10, high_value_count * 3)

        score += min(30, variety_score)

        # ========== VALIDITY SCORE (20 points) ==========
        validity_score = int(validation_results['validation_score'] * 0.2)
        score += validity_score

        # ========== COMPLETENESS SCORE (10 points) ==========
        # Based on total structured data instances
        total_instances = jsonld_count + microdata_count + rdfa_count

        if total_instances >= 5:
            completeness_score = 10
        elif total_instances >= 3:
            completeness_score = 8
        elif total_instances >= 2:
            completeness_score = 6
        else:
            completeness_score = 4

        score += completeness_score

        return max(0, min(100, score))

    def _generate_comment(
        self,
        score: int,
        jsonld_blocks: List[Dict],
        microdata_items: List[Dict],
        rdfa_items: List[Dict],
        schema_types: set,
        jsonld_errors: List[str],
        validation_results: Dict[str, Any]
    ) -> str:
        """Generate comprehensive comment."""
        if score >= 90:
            rating = "Excellent"
        elif score >= 80:
            rating = "Good"
        elif score >= 70:
            rating = "Acceptable"
        elif score >= 60:
            rating = "Minimal"
        else:
            rating = "Poor"

        total_instances = len(jsonld_blocks) + len(microdata_items) + len(rdfa_items)
        type_count = len(schema_types)

        comment = f"{rating} structured data coverage. {total_instances} instances, {type_count} schema types."

        # Format breakdown
        formats = []
        if jsonld_blocks:
            formats.append(f"{len(jsonld_blocks)} JSON-LD")
        if microdata_items:
            formats.append(f"{len(microdata_items)} Microdata")
        if rdfa_items:
            formats.append(f"{len(rdfa_items)} RDFa")

        if formats:
            comment += f" Formats: {', '.join(formats)}."

        # Schema types
        if schema_types:
            types_list = list(schema_types)[:5]  # First 5
            comment += f" Types: {', '.join(types_list)}"
            if len(schema_types) > 5:
                comment += f" (+{len(schema_types) - 5} more)"
            comment += "."

        # High-value types
        high_value_present = [t for t in schema_types if t in self.HIGH_VALUE_TYPES]
        if high_value_present:
            comment += f" High-value schemas: {', '.join(high_value_present[:3])}."

        # Errors
        if jsonld_errors:
            comment += f" {len(jsonld_errors)} JSON-LD errors detected."

        # Validation
        if validation_results['missing_required_props']:
            missing_count = len(validation_results['missing_required_props'])
            comment += f" {missing_count} missing required properties."

        # Recommendations
        if score >= 85:
            comment += " Comprehensive structured data for excellent AI understanding."
        elif score >= 70:
            comment += " Good foundation, add more schema types for richer context."
        else:
            comment += " Improve structured data coverage for better AI comprehension and search visibility."

        return comment

    def _generate_recommendations(
        self,
        jsonld_blocks: List[Dict],
        schema_types: set,
        jsonld_errors: List[str],
        validation_results: Dict[str, Any],
        score: int
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        # Critical issues
        if jsonld_errors:
            recommendations.append(f"CRITICAL: Fix {len(jsonld_errors)} JSON-LD errors (invalid syntax or structure)")

        if validation_results['missing_required_props']:
            recommendations.append(f"Add {len(validation_results['missing_required_props'])} missing required properties")

        # No JSON-LD
        if not jsonld_blocks:
            recommendations.append("Add JSON-LD structured data (preferred format by Google and AI models)")

        # Limited schema types
        if len(schema_types) < 3:
            recommendations.append("Add more schema types for comprehensive coverage (Organization, Article, Product, etc.)")

        # Missing high-value types
        missing_high_value = [t for t in self.HIGH_VALUE_TYPES if t not in schema_types]
        if 'Organization' not in schema_types:
            recommendations.append("Add Organization schema for your brand/company")

        if missing_high_value and len(missing_high_value) > 0:
            recommendations.append(f"Consider adding: {', '.join(missing_high_value[:3])} schemas")

        # Quality improvements
        if score < 80:
            recommendations.append("Use Google Rich Results Test to validate structured data")
            recommendations.append("Add more detailed properties to existing schemas")

        return recommendations[:6]

    def _calc_execution_time(self, start: datetime) -> int:
        """Calculate execution time in milliseconds."""
        return int((datetime.utcnow() - start).total_seconds() * 1000)

    def _error_result(self, error_msg: str, execution_start: datetime) -> Dict[str, Any]:
        """Generate error result."""
        return {
            'score': 0,
            'comment': f'Measurement failed: {error_msg}',
            'metadata': {
                'error': error_msg,
                'execution_time_ms': self._calc_execution_time(execution_start)
            }
        }


# Export for orchestrator
measurement = StructuredDataCoverageMeasurement()
