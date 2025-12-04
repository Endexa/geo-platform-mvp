"""
Schema.org Organization Check

Checks for Organization schema markup.
Important for Knowledge Graph and entity recognition.

Module: WI (Web Infrastructure)
Priority: High
Automation: Full
"""

import json
from typing import Dict, Any
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from scripts.base_measurement import BaseMeasurement
from utils import fetch_url, parse_html


class SchemaOrgOrganization(BaseMeasurement):
    """
    Check for Organization schema markup.

    Score:
    - 100: Complete Organization schema with all required fields
    - 75: Organization schema present but missing optional fields
    - 50: Organization schema present but incomplete
    - 0: No Organization schema found
    """

    def measure(self) -> Dict[str, Any]:
        """
        Check for Organization schema in JSON-LD.

        Returns:
            dict: Score and comment about Organization schema
        """
        response = fetch_url(self.url)
        if not response:
            return self._default_error_result("Failed to fetch URL")

        soup = parse_html(response.text)
        if not soup:
            return self._default_error_result("Failed to parse HTML")

        # Find all JSON-LD scripts
        json_ld_scripts = soup.find_all('script', type='application/ld+json')

        organization_schemas = []
        for script in json_ld_scripts:
            try:
                data = json.loads(script.string)

                # Handle both single objects and arrays
                if isinstance(data, dict):
                    data = [data]

                for item in data:
                    if item.get('@type') == 'Organization' or (isinstance(item.get('@type'), list) and 'Organization' in item.get('@type')):
                        organization_schemas.append(item)
            except (json.JSONDecodeError, AttributeError):
                continue

        if not organization_schemas:
            return {
                'score': 0.0,
                'comment': 'No Organization schema found. ✗ Add Organization markup to improve entity recognition.',
                'metadata': {
                    'schema_present': False,
                    'recommendation': 'Add JSON-LD with @type: Organization including name, url, logo, and contactPoint.'
                }
            }

        # Analyze the first Organization schema found
        org_schema = organization_schemas[0]

        # Required fields
        required_fields = ['name', 'url']
        # Important optional fields
        optional_fields = ['logo', 'description', 'contactPoint', 'sameAs', 'address']

        required_present = [field for field in required_fields if field in org_schema]
        optional_present = [field for field in optional_fields if field in org_schema]

        total_fields = len(required_fields) + len(optional_fields)
        present_fields = len(required_present) + len(optional_present)

        # Calculate score
        if len(required_present) == len(required_fields):
            # All required fields present
            completeness = (present_fields / total_fields) * 100

            if completeness >= 85:
                score = 100.0
                comment = f'Complete Organization schema found with {present_fields}/{total_fields} fields. ✓ Excellent for Knowledge Graph.'
            elif completeness >= 60:
                score = 75.0
                comment = f'Organization schema found with {present_fields}/{total_fields} fields. Good, but consider adding: {", ".join([f for f in optional_fields if f not in optional_present])}'
            else:
                score = 50.0
                comment = f'Organization schema incomplete ({present_fields}/{total_fields} fields). Add: {", ".join([f for f in optional_fields if f not in optional_present])}'
        else:
            # Missing required fields
            missing_required = [field for field in required_fields if field not in required_present]
            score = 25.0
            comment = f'Organization schema missing required fields: {", ".join(missing_required)}. ✗ Fix to improve entity recognition.'

        return {
            'score': score,
            'comment': comment,
            'metadata': {
                'schema_present': True,
                'schema_count': len(organization_schemas),
                'required_fields': required_present,
                'optional_fields': optional_present,
                'total_fields': present_fields,
                'schema_data': org_schema
            }
        }


if __name__ == "__main__":
    import sys
    test_url = sys.argv[1] if len(sys.argv) > 1 else "https://anthropic.com"

    measurement = SchemaOrgOrganization(test_url)
    result = measurement.run()
    print(f"Score: {result['score']}")
    print(f"Comment: {result['comment']}")
    print(f"Metadata: {result.get('metadata', {})}")
