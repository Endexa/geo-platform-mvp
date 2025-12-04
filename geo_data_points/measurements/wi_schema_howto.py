"""
WI-012: Schema.org - HowTo Validation

Validates HowTo schema.org structured data.
HowTo schemas help AI engines extract step-by-step instructions.
"""

from typing import Dict, Any
from geo_data_points.base import BaseMeasurement
from geo_data_points.utils.html_parser import HTMLAnalyzer
from loguru import logger
import json


class SchemaHowToMeasurement(BaseMeasurement):
    """Validate HowTo schema.org structured data."""

    def __init__(self):
        super().__init__(
            code="WI-012",
            name="Schema.org - HowTo",
            description="Validates HowTo schema.org structured data completeness and accuracy",
            category="Web Infrastructure",
            weight=0.85  # High value for procedural content extraction
        )

    async def measure(self, url: str, html: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Measure HowTo schema quality.

        Scoring:
        - 100: Perfect HowTo with 5+ complete steps, images, and tools/materials
        - 90: Complete HowTo with 3-5 steps
        - 70: Basic HowTo with 1-2 steps
        - 50: HowTo present but incomplete/invalid
        - 0: No HowTo schema

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

            # Extract all JSON-LD schemas
            json_ld_scripts = analyzer.get_json_ld()

            if not json_ld_scripts:
                return {
                    'score': 0,
                    'comment': 'No JSON-LD structured data found. If page contains instructions, add HowTo schema for AI extraction.'
                }

            # Find HowTo schemas
            howto_schemas = []
            for script in json_ld_scripts:
                try:
                    data = json.loads(script) if isinstance(script, str) else script

                    # Handle both single object and array
                    if isinstance(data, list):
                        for item in data:
                            if item.get('@type') == 'HowTo':
                                howto_schemas.append(item)
                    elif data.get('@type') == 'HowTo':
                        howto_schemas.append(data)
                except:
                    continue

            if not howto_schemas:
                # Check if page might need HowTo (contains step-by-step content)
                html_lower = html.lower()
                has_step_indicators = any(word in html_lower for word in ['step 1', 'step 2', 'instructions:', 'how to'])

                if has_step_indicators:
                    return {
                        'score': 0,
                        'comment': 'Page appears to contain step-by-step content but lacks HowTo schema. Add HowTo structured data to enable AI engines to extract your instructions.'
                    }
                else:
                    return {
                        'score': 0,
                        'comment': 'No HowTo schema found. If page contains instructions, add HowTo structured data.'
                    }

            # Validate HowTo schemas
            issues = []
            best_howto = None
            best_score = 0

            for howto in howto_schemas:
                current_issues = []
                current_score = 0

                # Check required fields
                if 'name' not in howto or not howto['name'].strip():
                    current_issues.append('Missing required "name" property (title)')
                else:
                    current_score += 10

                if 'step' not in howto:
                    current_issues.append('Missing required "step" property')
                    continue
                else:
                    current_score += 20

                # Validate steps
                steps = howto['step']
                if not isinstance(steps, list):
                    steps = [steps]

                step_count = len(steps)
                valid_steps = 0

                for i, step in enumerate(steps, 1):
                    # Check step type
                    step_type = step.get('@type')
                    if step_type not in ['HowToStep', 'HowToDirection']:
                        current_issues.append(f'Step {i}: Invalid @type "{step_type}"')
                        continue

                    # Check step text
                    has_text = 'text' in step and step['text'].strip()
                    has_name = 'name' in step and step['name'].strip()

                    if not (has_text or has_name):
                        current_issues.append(f'Step {i}: Missing step description (text or name)')
                        continue

                    # Validate step content length
                    step_text = step.get('text', step.get('name', ''))
                    if len(step_text) < 10:
                        current_issues.append(f'Step {i}: Description too short (<10 chars)')

                    valid_steps += 1

                if valid_steps == 0:
                    current_issues.append('No valid steps found')
                    continue

                current_score += min(50, valid_steps * 10)

                # Check optional but valuable fields
                if 'totalTime' in howto:
                    current_score += 5
                elif 'prepTime' in howto or 'performTime' in howto:
                    current_score += 3

                if 'tool' in howto or 'supply' in howto:
                    current_score += 5

                if 'image' in howto:
                    current_score += 5

                # Check for step images
                steps_with_images = sum(1 for s in steps if 'image' in s)
                if steps_with_images > 0:
                    current_score += min(5, steps_with_images)

                # Track best HowTo if multiple found
                if current_score > best_score:
                    best_score = current_score
                    best_howto = {
                        'data': howto,
                        'step_count': step_count,
                        'valid_steps': valid_steps,
                        'issues': current_issues
                    }
                    issues = current_issues

            if not best_howto:
                return {
                    'score': 0,
                    'comment': f'HowTo schema found but completely invalid. Issues: {"; ".join(issues[:3])}.'
                }

            # Calculate final score
            step_count = best_howto['step_count']
            valid_steps = best_howto['valid_steps']
            howto_data = best_howto['data']

            if valid_steps >= 5:
                base_score = 90
                comment = f'Excellent! HowTo with {valid_steps} complete steps.'
            elif valid_steps >= 3:
                base_score = 80
                comment = f'Great! HowTo with {valid_steps} complete steps.'
            elif valid_steps >= 1:
                base_score = 60
                comment = f'Good! HowTo with {valid_steps} step(s). Add more steps for better coverage.'
            else:
                base_score = 30
                comment = f'HowTo schema present but incomplete.'

            # Bonuses for rich content
            bonuses = []
            if 'totalTime' in howto_data or 'prepTime' in howto_data:
                base_score += 5
                bonuses.append('includes timing info')

            if 'tool' in howto_data or 'supply' in howto_data:
                base_score += 5
                bonuses.append('lists tools/materials')

            if 'image' in howto_data:
                base_score += 5
                bonuses.append('has image')

            if bonuses:
                comment += f' Bonus: {", ".join(bonuses)}.'

            # Cap at 100
            final_score = min(100, base_score)

            # Add issues if any
            if issues:
                penalty = min(15, len(issues) * 3)
                final_score = max(0, final_score - penalty)
                comment += f' Found {len(issues)} issue(s): {"; ".join(issues[:2])}{"..." if len(issues) > 2 else ""}.'

            return {
                'score': final_score,
                'comment': comment
            }

        except Exception as e:
            logger.error(f"Error measuring HowTo schema for {url}: {str(e)}")
            return {
                'score': 0,
                'comment': f'Measurement failed: {str(e)}'
            }


# Export for orchestrator
measurement = SchemaHowToMeasurement()
