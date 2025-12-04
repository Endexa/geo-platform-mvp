"""
WI-013: Schema.org - BreadcrumbList Validation

Validates BreadcrumbList schema.org structured data.
Breadcrumbs help AI engines understand site hierarchy and context.
"""

from typing import Dict, Any
from geo_data_points.base import BaseMeasurement
from geo_data_points.utils.html_parser import HTMLAnalyzer
from loguru import logger
import json


class SchemaBreadcrumbMeasurement(BaseMeasurement):
    """Validate BreadcrumbList schema.org structured data."""

    def __init__(self):
        super().__init__(
            code="WI-013",
            name="Schema.org - BreadcrumbList",
            description="Validates BreadcrumbList schema.org structured data completeness and accuracy",
            category="Web Infrastructure",
            weight=0.70  # Important for site hierarchy understanding
        )

    async def measure(self, url: str, html: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Measure BreadcrumbList schema quality.

        Scoring:
        - 100: Perfect breadcrumbs with 3+ levels, proper positioning
        - 90: Good breadcrumbs with 2-3 levels
        - 70: Basic breadcrumbs with 2 levels
        - 50: Breadcrumbs present but incomplete/invalid
        - 0: No breadcrumbs or homepage

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

            # Check if this is a homepage (breadcrumbs not required)
            from urllib.parse import urlparse
            parsed = urlparse(url)
            if parsed.path in ['/', '']:
                return {
                    'score': 100,
                    'comment': 'Homepage - breadcrumbs not required. Schema validation skipped.'
                }

            analyzer = HTMLAnalyzer(html, url)

            # Extract all JSON-LD schemas
            json_ld_scripts = analyzer.get_json_ld()

            if not json_ld_scripts:
                return {
                    'score': 0,
                    'comment': 'No JSON-LD structured data found. Add BreadcrumbList schema to help AI engines understand page context in site hierarchy.'
                }

            # Find BreadcrumbList schemas
            breadcrumb_schemas = []
            for script in json_ld_scripts:
                try:
                    data = json.loads(script) if isinstance(script, str) else script

                    # Handle both single object and array
                    if isinstance(data, list):
                        for item in data:
                            if item.get('@type') == 'BreadcrumbList':
                                breadcrumb_schemas.append(item)
                    elif data.get('@type') == 'BreadcrumbList':
                        breadcrumb_schemas.append(data)
                except:
                    continue

            if not breadcrumb_schemas:
                return {
                    'score': 0,
                    'comment': 'No BreadcrumbList schema found. Add breadcrumb structured data to help AI engines understand page context and site hierarchy.'
                }

            # Validate BreadcrumbList schemas
            issues = []
            best_breadcrumb = None
            best_score = 0

            for breadcrumb in breadcrumb_schemas:
                current_issues = []
                current_score = 0

                # Check required fields
                if 'itemListElement' not in breadcrumb:
                    current_issues.append('Missing required "itemListElement" property')
                    continue

                items = breadcrumb['itemListElement']
                if not isinstance(items, list):
                    items = [items]

                if len(items) == 0:
                    current_issues.append('Empty breadcrumb list')
                    continue

                # Validate breadcrumb items
                valid_items = 0
                has_position_errors = False

                for i, item in enumerate(items, 1):
                    # Check item type
                    if item.get('@type') != 'ListItem':
                        current_issues.append(f'Item {i}: Invalid @type (expected "ListItem")')
                        continue

                    # Check position
                    if 'position' not in item:
                        current_issues.append(f'Item {i}: Missing "position" property')
                        has_position_errors = True
                    elif item['position'] != i:
                        current_issues.append(f'Item {i}: Position mismatch (expected {i}, got {item["position"]})')
                        has_position_errors = True

                    # Check item field (must have name and URL or just item as object)
                    if 'item' in item:
                        item_obj = item['item']
                        if isinstance(item_obj, dict):
                            if '@id' not in item_obj and 'url' not in item_obj:
                                current_issues.append(f'Item {i}: Missing URL in item object')
                            if 'name' not in item_obj:
                                current_issues.append(f'Item {i}: Missing name in item object')
                            else:
                                valid_items += 1
                        elif isinstance(item_obj, str):
                            # URL as string
                            if 'name' not in item:
                                current_issues.append(f'Item {i}: Missing "name" property')
                            else:
                                valid_items += 1
                    elif 'name' in item:
                        # Name without item (acceptable for last item)
                        valid_items += 1
                    else:
                        current_issues.append(f'Item {i}: Missing both "item" and "name" properties')

                if valid_items == 0:
                    current_issues.append('No valid breadcrumb items found')
                    continue

                current_score = min(100, valid_items * 30)

                # Track best breadcrumb if multiple found
                if current_score > best_score:
                    best_score = current_score
                    best_breadcrumb = {
                        'data': breadcrumb,
                        'item_count': len(items),
                        'valid_items': valid_items,
                        'issues': current_issues
                    }
                    issues = current_issues

            if not best_breadcrumb:
                return {
                    'score': 0,
                    'comment': f'BreadcrumbList schema found but completely invalid. Issues: {"; ".join(issues[:3])}.'
                }

            # Calculate final score
            item_count = best_breadcrumb['item_count']
            valid_items = best_breadcrumb['valid_items']

            # Base score from depth
            if valid_items >= 4:
                base_score = 100
                comment = f'Perfect! Breadcrumb with {valid_items} levels showing deep site hierarchy.'
            elif valid_items == 3:
                base_score = 90
                comment = f'Excellent! Breadcrumb with {valid_items} levels showing good site structure.'
            elif valid_items == 2:
                base_score = 70
                comment = f'Good! Breadcrumb with {valid_items} levels. Consider adding more hierarchy levels if applicable.'
            else:
                base_score = 50
                comment = f'Basic breadcrumb with only {valid_items} level(s). Add more hierarchy for better context.'

            # Penalties for issues
            if issues:
                penalty = min(25, len(issues) * 5)
                base_score = max(0, base_score - penalty)
                comment += f' Found {len(issues)} issue(s): {"; ".join(issues[:2])}{"..." if len(issues) > 2 else ""}.'

            return {
                'score': base_score,
                'comment': comment
            }

        except Exception as e:
            logger.error(f"Error measuring BreadcrumbList schema for {url}: {str(e)}")
            return {
                'score': 0,
                'comment': f'Measurement failed: {str(e)}'
            }


# Export for orchestrator
measurement = SchemaBreadcrumbMeasurement()
