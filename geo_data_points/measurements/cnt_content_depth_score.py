"""
CNT-007: Content Depth Score

Measures content depth using multiple signals: word count, headings, lists,
multimedia elements, external references, and structural complexity.

This is a composite metric that evaluates how thoroughly a topic is covered.
AI models strongly prefer comprehensive, well-structured content.
"""

from typing import Dict, Any, List
from geo_data_points.base import BaseMeasurement
from geo_data_points.utils.html_parser import HTMLAnalyzer
from geo_data_points.utils.content_analyzer import ContentAnalyzer
from loguru import logger


class ContentDepthScoreMeasurement(BaseMeasurement):
    """Measure content depth using composite signals."""

    def __init__(self):
        super().__init__(
            code="CNT-007",
            name="Content Depth Score",
            description="Measures content depth using word count, structure, multimedia, and references",
            category="Content",
            weight=0.95  # Critical for AI content quality assessment
        )

    async def measure(self, url: str, html: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Measure comprehensive content depth.

        Scoring methodology:
        - Base score from word count (0-40 points)
        - Structural depth: headings hierarchy (0-20 points)
        - Content richness: lists, tables, quotes (0-15 points)
        - Multimedia: images, videos (0-10 points)
        - External references: links, citations (0-10 points)
        - Paragraph quality: average length, variety (0-5 points)

        Total: 0-100 points

        Args:
            url: Target URL to analyze
            html: HTML content to parse
            metadata: Unused

        Returns:
            Dict with score (0-100) and detailed comment with breakdown
        """
        try:
            if not html:
                return {
                    'score': 0,
                    'comment': 'No HTML content provided for analysis.'
                }

            # Initialize analyzers
            html_analyzer = HTMLAnalyzer(html, url)
            main_text = html_analyzer.get_main_content_text()

            if not main_text or len(main_text.strip()) < 100:
                return {
                    'score': 0,
                    'comment': 'Insufficient content for depth analysis (<100 chars). Add substantial, structured content with multiple sections.'
                }

            content_analyzer = ContentAnalyzer(main_text)

            # ========== 1. WORD COUNT SCORE (0-40 points) ==========
            words = main_text.split()
            word_count = len(words)

            if word_count >= 2500:
                word_score = 40
            elif word_count >= 2000:
                word_score = 38
            elif word_count >= 1500:
                word_score = 35
            elif word_count >= 1200:
                word_score = 32
            elif word_count >= 1000:
                word_score = 28
            elif word_count >= 800:
                word_score = 24
            elif word_count >= 600:
                word_score = 18
            elif word_count >= 400:
                word_score = 12
            elif word_count >= 200:
                word_score = 6
            else:
                word_score = 2

            # ========== 2. STRUCTURAL DEPTH (0-20 points) ==========
            headings = html_analyzer.get_headings()
            heading_levels = [h['level'] for h in headings]

            # Count headings by level
            h1_count = heading_levels.count(1)
            h2_count = heading_levels.count(2)
            h3_count = heading_levels.count(3)
            h4_count = heading_levels.count(4)

            # Calculate structural score
            structure_score = 0

            # H1 presence (required)
            if h1_count == 1:
                structure_score += 4
            elif h1_count == 0:
                structure_score += 0  # Major penalty
            else:
                structure_score += 1  # Multiple H1s is bad

            # H2 subheadings (main sections)
            if h2_count >= 5:
                structure_score += 8
            elif h2_count >= 3:
                structure_score += 6
            elif h2_count >= 2:
                structure_score += 4
            elif h2_count >= 1:
                structure_score += 2

            # H3 sub-sections (depth indicator)
            if h3_count >= 5:
                structure_score += 6
            elif h3_count >= 3:
                structure_score += 4
            elif h3_count >= 1:
                structure_score += 2

            # H4 deep hierarchy (bonus for very detailed content)
            if h4_count >= 2:
                structure_score += 2

            # Cap at 20
            structure_score = min(20, structure_score)

            # ========== 3. CONTENT RICHNESS (0-15 points) ==========
            richness_score = 0

            # Lists (ordered and unordered)
            lists = html_analyzer.get_lists()
            if lists:
                list_count = len(lists)
                if list_count >= 5:
                    richness_score += 5
                elif list_count >= 3:
                    richness_score += 4
                elif list_count >= 1:
                    richness_score += 2

            # Tables (structured data presentation)
            tables = html_analyzer.get_tables()
            if tables:
                table_count = len(tables)
                if table_count >= 3:
                    richness_score += 4
                elif table_count >= 1:
                    richness_score += 2

            # Blockquotes/citations
            citations = content_analyzer.detect_citations()
            quote_count = citations.get('quote_count', 0)
            if quote_count >= 3:
                richness_score += 3
            elif quote_count >= 1:
                richness_score += 2

            # Code blocks (technical depth for tech content)
            if '<code' in html.lower() or '<pre' in html.lower():
                richness_score += 3

            # Cap at 15
            richness_score = min(15, richness_score)

            # ========== 4. MULTIMEDIA ELEMENTS (0-10 points) ==========
            multimedia_score = 0

            # Images
            images = html_analyzer.get_images()
            if images:
                image_count = len(images)
                if image_count >= 8:
                    multimedia_score += 5
                elif image_count >= 5:
                    multimedia_score += 4
                elif image_count >= 3:
                    multimedia_score += 3
                elif image_count >= 1:
                    multimedia_score += 2

            # Videos
            has_video = html_analyzer.has_video_content()
            if has_video:
                multimedia_score += 3

            # Audio
            if '<audio' in html.lower():
                multimedia_score += 2

            # Cap at 10
            multimedia_score = min(10, multimedia_score)

            # ========== 5. EXTERNAL REFERENCES (0-10 points) ==========
            reference_score = 0

            # External links (authority signals)
            external_links = html_analyzer.get_external_links()
            if external_links:
                ext_count = len(external_links)
                if ext_count >= 10:
                    reference_score += 6
                elif ext_count >= 5:
                    reference_score += 5
                elif ext_count >= 3:
                    reference_score += 4
                elif ext_count >= 1:
                    reference_score += 2

            # Citations/references
            reference_count = citations.get('reference_count', 0)
            if reference_count >= 5:
                reference_score += 4
            elif reference_count >= 2:
                reference_score += 3
            elif reference_count >= 1:
                reference_score += 2

            # Cap at 10
            reference_score = min(10, reference_score)

            # ========== 6. PARAGRAPH QUALITY (0-5 points) ==========
            quality_score = 0

            # Paragraph count and average length
            paragraph_count = content_analyzer.get_paragraph_count()
            avg_paragraph_length = content_analyzer.get_average_paragraph_length()

            # Good paragraph structure
            if paragraph_count >= 10 and 50 <= avg_paragraph_length <= 150:
                quality_score += 3
            elif paragraph_count >= 5 and 40 <= avg_paragraph_length <= 200:
                quality_score += 2
            elif paragraph_count >= 3:
                quality_score += 1

            # Sentence variety
            avg_sentence_length = content_analyzer.get_average_sentence_length()
            if 15 <= avg_sentence_length <= 25:  # Good readability range
                quality_score += 2
            elif 12 <= avg_sentence_length <= 30:
                quality_score += 1

            # Cap at 5
            quality_score = min(5, quality_score)

            # ========== CALCULATE TOTAL SCORE ==========
            total_score = (
                word_score +
                structure_score +
                richness_score +
                multimedia_score +
                reference_score +
                quality_score
            )

            # Cap at 100
            total_score = min(100, total_score)

            # ========== GENERATE DETAILED COMMENT ==========
            # Determine overall rating
            if total_score >= 90:
                rating = "Exceptional depth"
            elif total_score >= 80:
                rating = "Excellent depth"
            elif total_score >= 70:
                rating = "Good depth"
            elif total_score >= 60:
                rating = "Moderate depth"
            elif total_score >= 40:
                rating = "Shallow content"
            else:
                rating = "Very shallow content"

            # Build detailed breakdown
            comment = f'{rating} (Score: {total_score}/100). '

            # Add component breakdown
            breakdown_parts = [
                f'Words: {word_count:,} ({word_score}/40)',
                f'Structure: H1:{h1_count} H2:{h2_count} H3:{h3_count} ({structure_score}/20)',
                f'Richness: Lists:{len(lists)} Tables:{len(tables)} ({richness_score}/15)',
                f'Media: {len(images)} images ({multimedia_score}/10)',
                f'References: {len(external_links)} external links ({reference_score}/10)',
                f'Quality: {paragraph_count} paragraphs ({quality_score}/5)'
            ]

            comment += ' | '.join(breakdown_parts) + '.'

            # ========== ACTIONABLE RECOMMENDATIONS ==========
            recommendations = []

            if word_score < 28:
                recommendations.append(f'Expand content to 1000+ words (current: {word_count})')

            if structure_score < 10:
                if h2_count < 3:
                    recommendations.append('Add more H2 sections (aim for 3-5)')
                if h3_count < 2:
                    recommendations.append('Add H3 subsections for depth')

            if richness_score < 8:
                if len(lists) == 0:
                    recommendations.append('Add lists for better scanability')
                if len(tables) == 0 and word_count > 800:
                    recommendations.append('Consider tables for structured data')

            if multimedia_score < 5:
                if len(images) < 3:
                    recommendations.append('Add relevant images (aim for 3-5)')

            if reference_score < 5:
                if len(external_links) < 3:
                    recommendations.append('Add external references to authoritative sources')

            if recommendations:
                comment += f' Improvements: {"; ".join(recommendations[:3])}.'

            # ========== PERFORMANCE INSIGHTS ==========
            # Add insights for high-performing content
            if total_score >= 80:
                strengths = []
                if word_score >= 32:
                    strengths.append('comprehensive length')
                if structure_score >= 15:
                    strengths.append('excellent hierarchy')
                if richness_score >= 10:
                    strengths.append('rich formatting')
                if multimedia_score >= 7:
                    strengths.append('good multimedia')

                if strengths:
                    comment += f' Strengths: {", ".join(strengths)}.'

            return {
                'score': total_score,
                'comment': comment
            }

        except Exception as e:
            logger.error(f"Error measuring content depth for {url}: {str(e)}")
            return {
                'score': 0,
                'comment': f'Measurement failed: {str(e)}'
            }


# Export for orchestrator
measurement = ContentDepthScoreMeasurement()
