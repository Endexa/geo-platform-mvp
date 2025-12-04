"""
CNT-005: Heading Hierarchy

Validates proper heading structure (H1-H6) for content organization.
AI models use heading hierarchy to understand content structure and extract key sections.
"""

from typing import Dict, Any
from geo_data_points.base import BaseMeasurement
from geo_data_points.utils.html_parser import HTMLAnalyzer
from loguru import logger


class HeadingHierarchyMeasurement(BaseMeasurement):
    """Validate heading hierarchy structure."""

    def __init__(self):
        super().__init__(
            code="CNT-005",
            name="Heading Hierarchy",
            description="Validates proper heading structure (H1-H6) for content organization",
            category="Content",
            weight=0.80  # Important for content structure understanding
        )

    async def measure(self, url: str, html: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Measure heading hierarchy quality.

        Scoring:
        - 100: Perfect hierarchy (1 H1, logical H2-H3 structure, no skips)
        - 90: Good hierarchy (1 H1, minor issues)
        - 75: Decent hierarchy (some issues)
        - 50: Poor hierarchy (multiple H1s or major skips)
        - 25: Very poor hierarchy
        - 0: No headings found

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

            # Get all headings
            headings = analyzer.get_headings()

            if not headings:
                return {
                    'score': 0,
                    'comment': 'No headings found. Add H1-H3 headings to structure content for AI model comprehension. Headings help AI extract key sections.'
                }

            # Analyze heading structure
            issues = []
            warnings = []
            score = 100

            # Check H1 count
            h1_count = sum(1 for h in headings if h['level'] == 1)

            if h1_count == 0:
                issues.append('Missing H1 heading (page title)')
                score -= 30
            elif h1_count > 1:
                issues.append(f'Multiple H1 headings ({h1_count}) - should have exactly 1')
                score -= 20

            # Check heading levels and hierarchy
            if h1_count == 1:
                # Verify hierarchy doesn't skip levels
                levels_used = sorted(set(h['level'] for h in headings))

                for i in range(len(levels_used) - 1):
                    if levels_used[i + 1] - levels_used[i] > 1:
                        skipped_level = levels_used[i] + 1
                        issues.append(f'Skipped heading level (H{skipped_level}) - go from H{levels_used[i]} to H{levels_used[i+1]}')
                        score -= 15

            # Validate heading sequence
            prev_level = 0
            deep_jumps = 0

            for i, heading in enumerate(headings):
                current_level = heading['level']

                # Check for deep jumps (e.g., H2 to H5)
                if current_level > prev_level + 1 and prev_level > 0:
                    deep_jumps += 1
                    if deep_jumps <= 2:
                        warnings.append(f'Heading {i+1}: Jump from H{prev_level} to H{current_level}')

                prev_level = current_level

            if deep_jumps > 0:
                score -= min(20, deep_jumps * 5)

            # Check heading content quality
            empty_headings = sum(1 for h in headings if not h['text'].strip())
            if empty_headings > 0:
                issues.append(f'{empty_headings} empty heading(s) - add descriptive text')
                score -= empty_headings * 5

            # Check heading length
            short_headings = sum(1 for h in headings if len(h['text'].strip()) < 3)
            if short_headings > 0:
                warnings.append(f'{short_headings} very short heading(s) (<3 chars) - make more descriptive')
                score -= short_headings * 2

            # Count heading levels
            h2_count = sum(1 for h in headings if h['level'] == 2)
            h3_count = sum(1 for h in headings if h['level'] == 3)

            # Bonus for good structure
            if h2_count >= 3 and h3_count >= 2:
                score = min(100, score + 5)

            # Cap score
            score = max(0, min(100, score))

            # Generate comment
            if score >= 90:
                comment = f'Excellent heading hierarchy! {h1_count} H1, {h2_count} H2, {h3_count} H3 headings. Clear structure for AI extraction.'
            elif score >= 75:
                comment = f'Good heading hierarchy. {h1_count} H1, {h2_count} H2, {h3_count} H3 headings.'
            elif score >= 50:
                comment = f'Acceptable heading hierarchy with issues. {h1_count} H1, {h2_count} H2, {h3_count} H3 headings.'
            else:
                comment = f'Poor heading hierarchy. {h1_count} H1, {h2_count} H2, {h3_count} H3 headings.'

            # Add issues
            if issues:
                comment += f' Critical issues: {"; ".join(issues)}.'

            if warnings and score < 90:
                comment += f' Warnings: {"; ".join(warnings[:2])}{"..." if len(warnings) > 2 else ""}.'

            # Recommendations
            if h2_count < 2:
                comment += ' Tip: Add more H2 subheadings to break content into sections.'
            elif h3_count == 0 and h2_count > 0:
                comment += ' Tip: Add H3 subheadings under H2 sections for deeper structure.'

            return {
                'score': score,
                'comment': comment
            }

        except Exception as e:
            logger.error(f"Error measuring heading hierarchy for {url}: {str(e)}")
            return {
                'score': 0,
                'comment': f'Measurement failed: {str(e)}'
            }


# Export for orchestrator
measurement = HeadingHierarchyMeasurement()
