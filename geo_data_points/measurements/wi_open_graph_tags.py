"""
WI-019: Open Graph Tags

Validates Open Graph meta tags for social media sharing.
OG tags ensure proper content representation when shared on social platforms and understood by AI.
"""

from typing import Dict, Any, List
from geo_data_points.base import BaseMeasurement
from geo_data_points.utils.html_parser import HTMLAnalyzer
from loguru import logger


class OpenGraphTagsMeasurement(BaseMeasurement):
    """Validate Open Graph tags implementation."""

    def __init__(self):
        super().__init__(
            code="WI-019",
            name="Open Graph Tags",
            description="Validates Open Graph meta tags for social sharing and AI understanding",
            category="Web Infrastructure",
            weight=0.75  # Important for social sharing and AI metadata
        )

    async def measure(self, url: str, html: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Measure Open Graph tags completeness and quality.

        Scoring:
        - 100: All required OG tags present + optional tags (image, description, type, site_name)
        - 90: All required tags (og:title, og:url, og:image, og:description)
        - 80: Required tags minus 1
        - 60: Only og:title and og:url
        - 40: Only og:title or og:url
        - 0: No OG tags

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
            meta_tags = analyzer.get_meta_tags()

            # Extract Open Graph tags (they have property="og:..." or name="og:...")
            og_tags = {}
            for key, value in meta_tags.items():
                if key.startswith('og:'):
                    og_tags[key] = value

            if not og_tags:
                return {
                    'score': 0,
                    'comment': 'No Open Graph tags found. Critical for social media sharing! Add OG tags (<meta property="og:title" content="...">) to ensure proper content representation on Facebook, LinkedIn, Twitter, and other platforms. This also helps AI understand page metadata.'
                }

            # Define required and recommended tags
            required_tags = {
                'og:title': 'Page title',
                'og:url': 'Canonical URL',
                'og:image': 'Preview image',
                'og:description': 'Page description'
            }

            recommended_tags = {
                'og:type': 'Content type',
                'og:site_name': 'Site name',
                'og:locale': 'Content locale'
            }

            # Check which tags are present
            present_required = []
            missing_required = []

            for tag, description in required_tags.items():
                if tag in og_tags and og_tags[tag].strip():
                    present_required.append(tag)
                else:
                    missing_required.append((tag, description))

            present_recommended = []
            missing_recommended = []

            for tag, description in recommended_tags.items():
                if tag in og_tags and og_tags[tag].strip():
                    present_recommended.append(tag)
                else:
                    missing_recommended.append((tag, description))

            # ========== SCORING ==========
            required_count = len(present_required)

            if required_count == 4 and len(present_recommended) >= 2:
                score = 100
                rating = "Perfect"
            elif required_count == 4:
                score = 90
                rating = "Excellent"
            elif required_count == 3:
                score = 80
                rating = "Good"
            elif required_count == 2:
                score = 60
                rating = "Moderate"
            elif required_count == 1:
                score = 40
                rating = "Poor"
            else:
                score = 0
                rating = "Insufficient"

            # ========== QUALITY CHECKS ==========
            issues = []
            warnings = []

            # Check og:title
            if 'og:title' in og_tags:
                og_title = og_tags['og:title']
                title_length = len(og_title)

                if title_length > 95:
                    warnings.append(f'og:title too long ({title_length} chars, may be truncated)')
                    score = max(0, score - 5)
                elif title_length < 10:
                    warnings.append(f'og:title too short ({title_length} chars)')
                    score = max(0, score - 5)

            # Check og:description
            if 'og:description' in og_tags:
                og_desc = og_tags['og:description']
                desc_length = len(og_desc)

                if desc_length > 300:
                    warnings.append(f'og:description too long ({desc_length} chars, may be truncated)')
                    score = max(0, score - 5)
                elif desc_length < 50:
                    warnings.append(f'og:description too short ({desc_length} chars)')
                    score = max(0, score - 5)

            # Check og:image
            if 'og:image' in og_tags:
                og_image = og_tags['og:image']

                # Check if image URL is absolute
                if not og_image.startswith('http'):
                    issues.append('og:image should be absolute URL (https://...)')
                    score = max(0, score - 10)

                # Check for image dimensions (recommended: 1200x630)
                if 'og:image:width' in og_tags and 'og:image:height' in og_tags:
                    try:
                        width = int(og_tags['og:image:width'])
                        height = int(og_tags['og:image:height'])

                        if width >= 1200 and height >= 630:
                            present_recommended.append('og:image dimensions')
                        else:
                            warnings.append(f'og:image dimensions ({width}x{height}) smaller than recommended (1200x630)')
                    except:
                        pass

            # Check og:url
            if 'og:url' in og_tags:
                og_url = og_tags['og:url']

                # Should be absolute URL
                if not og_url.startswith('http'):
                    issues.append('og:url should be absolute URL')
                    score = max(0, score - 10)

                # Should match current URL (ignoring parameters)
                from urllib.parse import urlparse
                current_base = urlparse(url)._replace(query='', fragment='').geturl()
                og_base = urlparse(og_url)._replace(query='', fragment='').geturl()

                if current_base != og_base:
                    warnings.append('og:url differs from current URL (may be intentional)')

            # Check og:type
            if 'og:type' in og_tags:
                og_type = og_tags['og:type']
                valid_types = ['website', 'article', 'blog', 'product', 'video', 'music']

                if og_type not in valid_types:
                    warnings.append(f'og:type "{og_type}" is uncommon (use website, article, product, etc.)')

            # ========== GENERATE COMMENT ==========
            comment = f'{rating} Open Graph implementation. {len(present_required)}/4 required tags present'

            if present_recommended:
                comment += f', {len(present_recommended)} recommended tags.'
            else:
                comment += '.'

            # List present tags
            all_present = present_required + present_recommended
            if all_present:
                comment += f' Present: {", ".join(all_present)}.'

            # List missing required tags
            if missing_required:
                missing_list = [f'{tag} ({desc})' for tag, desc in missing_required]
                comment += f' Missing required: {"; ".join(missing_list)}.'

            # Add issues
            if issues:
                comment += f' Issues: {"; ".join(issues)}.'

            # Add warnings
            if warnings:
                comment += f' Warnings: {"; ".join(warnings[:2])}{"..." if len(warnings) > 2 else ""}.'

            # ========== RECOMMENDATIONS ==========
            if missing_required:
                comment += f' Critical: Add missing OG tags immediately for proper social sharing.'

            if not missing_required and len(present_recommended) < 2:
                comment += ' Improvement: Add recommended tags (og:type, og:site_name, og:locale) for richer metadata.'

            # ========== CONTEXT ==========
            if score >= 85:
                comment += ' Strong OG implementation for social media and AI metadata understanding.'
            elif score >= 60:
                comment += ' Acceptable OG tags, but incomplete. Complete all required tags for optimal social sharing.'
            else:
                comment += ' Insufficient OG tags. Critical for social media appearance and AI metadata extraction.'

            return {
                'score': score,
                'comment': comment,
                'metadata': {
                    'og_tags_count': len(og_tags),
                    'required_present': len(present_required),
                    'required_missing': len(missing_required),
                    'recommended_present': len(present_recommended)
                }
            }

        except Exception as e:
            logger.error(f"Error measuring Open Graph tags for {url}: {str(e)}")
            return {
                'score': 0,
                'comment': f'Measurement failed: {str(e)}'
            }


# Export for orchestrator
measurement = OpenGraphTagsMeasurement()
