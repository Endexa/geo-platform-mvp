"""
CNT-004: Citation Ratio

Measures the ratio of citations, quotes, and references in content.
AI models favor well-sourced content with proper attribution.
"""

from typing import Dict, Any
from geo_data_points.base import BaseMeasurement
from geo_data_points.utils.html_parser import HTMLAnalyzer
from geo_data_points.utils.content_analyzer import ContentAnalyzer
from loguru import logger


class CitationRatioMeasurement(BaseMeasurement):
    """Measure citation and reference density in content."""

    def __init__(self):
        super().__init__(
            code="CNT-004",
            name="Citation Ratio",
            description="Measures density of citations, quotes, and references in content",
            category="Content",
            weight=0.85  # High value for content authority
        )

    async def measure(self, url: str, html: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Measure citation ratio.

        Scoring:
        - 100: >5% citation ratio (highly referenced)
        - 90: 3-5% citation ratio
        - 80: 2-3% citation ratio
        - 70: 1-2% citation ratio
        - 50: 0.5-1% citation ratio
        - 30: <0.5% citation ratio
        - 0: No citations found

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
                    'comment': 'Insufficient content for citation analysis (<100 chars).'
                }

            # Analyze citations
            content_analyzer = ContentAnalyzer(main_text)

            # Detect citations
            citations = content_analyzer.detect_citations()

            # Count words
            words = main_text.split()
            total_words = len(words)

            if total_words == 0:
                return {
                    'score': 0,
                    'comment': 'No content words found.'
                }

            # Count different types of citations
            quote_count = citations.get('quote_count', 0)
            reference_count = citations.get('reference_count', 0)
            total_citations = quote_count + reference_count

            if total_citations == 0:
                # Check HTML for citation-specific elements
                html_lower = html.lower()
                has_citation_elements = any(
                    elem in html_lower
                    for elem in ['<cite', '<blockquote', 'class="citation', 'class="reference']
                )

                if has_citation_elements:
                    return {
                        'score': 30,
                        'comment': 'Citation elements found in HTML but not detected in text. Ensure proper citation formatting for AI models.'
                    }
                else:
                    return {
                        'score': 0,
                        'comment': 'No citations detected. Add quotes, references, and source attributions to improve content authority for AI models. Well-sourced content is prioritized.'
                    }

            # Calculate citation ratio (citations per 100 words)
            citation_ratio = (total_citations / total_words) * 100

            # Determine score
            if citation_ratio >= 5:
                score = 100
                comment = f'Exceptional citation density: {citation_ratio:.2f}% ({total_citations} citations in {total_words} words). Highly authoritative for AI models!'
            elif citation_ratio >= 3:
                score = 90
                comment = f'Excellent citation density: {citation_ratio:.2f}% ({total_citations} citations in {total_words} words). Well-sourced content for AI!'
            elif citation_ratio >= 2:
                score = 80
                comment = f'Good citation density: {citation_ratio:.2f}% ({total_citations} citations in {total_words} words). Strong authority signals.'
            elif citation_ratio >= 1:
                score = 70
                comment = f'Moderate citation density: {citation_ratio:.2f}% ({total_citations} citations in {total_words} words). Add more references for better authority.'
            elif citation_ratio >= 0.5:
                score = 50
                comment = f'Low citation density: {citation_ratio:.2f}% ({total_citations} citations in {total_words} words). Increase citations to improve content credibility.'
            else:
                score = 30
                comment = f'Very low citation density: {citation_ratio:.2f}% ({total_citations} citations in {total_words} words). Add substantially more references and quotes.'

            # Add breakdown
            if quote_count > 0 and reference_count > 0:
                comment += f' Citations: {quote_count} quotes, {reference_count} references.'
            elif quote_count > 0:
                comment += f' Found: {quote_count} quotes. Add more explicit references for completeness.'
            elif reference_count > 0:
                comment += f' Found: {reference_count} references. Add quotes from sources for richness.'

            # Check for external links (additional authority signal)
            external_links = analyzer.get_external_links()
            if external_links:
                external_count = len(external_links)
                comment += f' {external_count} external link(s) found (additional authority signal).'
                # Bonus for external links
                score = min(100, score + min(10, external_count))

            # Recommendations
            if citation_ratio < 2:
                comment += ' Tip: Quote experts, cite studies, reference authoritative sources.'

            return {
                'score': score,
                'comment': comment
            }

        except Exception as e:
            logger.error(f"Error measuring citation ratio for {url}: {str(e)}")
            return {
                'score': 0,
                'comment': f'Measurement failed: {str(e)}'
            }


# Export for orchestrator
measurement = CitationRatioMeasurement()
