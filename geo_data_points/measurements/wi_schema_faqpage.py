"""
WI-011: Schema.org - FAQPage Validation

Validates FAQPage schema.org structured data.
FAQ schemas are highly valuable for AI engines to extract Q&A content directly.
"""

from typing import Dict, Any, List
from geo_data_points.base import BaseMeasurement
from geo_data_points.utils.html_parser import HTMLAnalyzer
from loguru import logger
import json


class SchemaFAQPageMeasurement(BaseMeasurement):
    """Validate FAQPage schema.org structured data."""

    def __init__(self):
        super().__init__(
            code="WI-011",
            name="Schema.org - FAQPage",
            description="Validates FAQPage schema.org structured data completeness and accuracy",
            category="Web Infrastructure",
            weight=0.90  # Very high value for AI Q&A extraction
        )

    async def measure(self, url: str, html: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Measure FAQPage schema quality.

        Scoring:
        - 100: Perfect FAQPage with 5+ complete Q&A pairs
        - 90: 3-4 complete Q&A pairs
        - 70: 1-2 complete Q&A pairs
        - 50: FAQPage present but incomplete/invalid
        - 0: No FAQPage schema

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
                    'comment': 'No JSON-LD structured data found. Add FAQPage schema for AI Q&A extraction. FAQ content is highly valuable for generative engines.'
                }

            # Find FAQPage schemas
            faq_schemas = []
            for script in json_ld_scripts:
                try:
                    data = json.loads(script) if isinstance(script, str) else script

                    # Handle both single object and array
                    if isinstance(data, list):
                        for item in data:
                            if item.get('@type') == 'FAQPage':
                                faq_schemas.append(item)
                    elif data.get('@type') == 'FAQPage':
                        faq_schemas.append(data)
                except:
                    continue

            if not faq_schemas:
                return {
                    'score': 0,
                    'comment': 'No FAQPage schema found. Add FAQPage structured data to enable AI engines to extract your Q&A content directly. This significantly improves GEO visibility.'
                }

            # Validate FAQPage schemas
            total_questions = 0
            complete_qa_pairs = 0
            incomplete_qa_pairs = 0
            issues = []

            for faq in faq_schemas:
                # Check for mainEntity
                if 'mainEntity' not in faq:
                    issues.append('FAQPage missing required "mainEntity" property')
                    continue

                main_entity = faq['mainEntity']
                if not isinstance(main_entity, list):
                    main_entity = [main_entity]

                for qa in main_entity:
                    total_questions += 1

                    # Validate Question type
                    if qa.get('@type') != 'Question':
                        issues.append(f'Question {total_questions}: Invalid @type (expected "Question")')
                        incomplete_qa_pairs += 1
                        continue

                    # Check required fields
                    has_name = 'name' in qa and qa['name'].strip()
                    has_accepted_answer = 'acceptedAnswer' in qa

                    if not has_name:
                        issues.append(f'Question {total_questions}: Missing "name" property (the question text)')
                        incomplete_qa_pairs += 1
                        continue

                    if not has_accepted_answer:
                        issues.append(f'Question {total_questions}: Missing "acceptedAnswer" property')
                        incomplete_qa_pairs += 1
                        continue

                    # Validate Answer
                    answer = qa['acceptedAnswer']
                    if answer.get('@type') != 'Answer':
                        issues.append(f'Question {total_questions}: Answer has invalid @type (expected "Answer")')
                        incomplete_qa_pairs += 1
                        continue

                    if 'text' not in answer or not answer['text'].strip():
                        issues.append(f'Question {total_questions}: Answer missing "text" property')
                        incomplete_qa_pairs += 1
                        continue

                    # Validate content quality
                    question_text = qa['name'].strip()
                    answer_text = answer['text'].strip()

                    if len(question_text) < 10:
                        issues.append(f'Question {total_questions}: Question too short (<10 chars)')

                    if len(answer_text) < 20:
                        issues.append(f'Question {total_questions}: Answer too short (<20 chars)')

                    # Check if question ends with ?
                    if not question_text.endswith('?'):
                        issues.append(f'Question {total_questions}: Question should end with "?"')

                    # All validations passed
                    complete_qa_pairs += 1

            # Calculate score
            if complete_qa_pairs == 0:
                return {
                    'score': 0,
                    'comment': f'FAQPage schema found but no valid Q&A pairs. Issues: {"; ".join(issues[:3])}. Fix schema validation errors.'
                }

            # Base score from number of complete Q&A pairs
            if complete_qa_pairs >= 5:
                score = 100
                comment = f'Perfect! FAQPage with {complete_qa_pairs} complete Q&A pairs. Excellent for AI extraction.'
            elif complete_qa_pairs >= 3:
                score = 90
                comment = f'Great! FAQPage with {complete_qa_pairs} complete Q&A pairs. Consider adding more questions for richer content.'
            elif complete_qa_pairs >= 1:
                score = 70
                comment = f'Good! FAQPage with {complete_qa_pairs} complete Q&A pair(s). Add more questions (aim for 5+) for better AI coverage.'
            else:
                score = 50
                comment = f'FAQPage found but incomplete. {incomplete_qa_pairs} invalid Q&A pairs. Fix validation errors.'

            # Penalties for issues
            if issues:
                penalty = min(20, len(issues) * 2)
                score = max(0, score - penalty)
                comment += f' Found {len(issues)} issue(s): {"; ".join(issues[:2])}{"..." if len(issues) > 2 else ""}.'

            # Bonus for exceptional coverage
            if complete_qa_pairs >= 10:
                score = min(100, score + 5)
                comment = comment.replace('Perfect!', 'Exceptional!')

            return {
                'score': score,
                'comment': comment
            }

        except Exception as e:
            logger.error(f"Error measuring FAQPage schema for {url}: {str(e)}")
            return {
                'score': 0,
                'comment': f'Measurement failed: {str(e)}'
            }


# Export for orchestrator
measurement = SchemaFAQPageMeasurement()
