"""
WI-014: Schema.org - Article Validation

Validates Article schema.org structured data (Article, NewsArticle, BlogPosting).
Article schemas help AI engines understand content structure, authorship, and publishing details.
"""

from typing import Dict, Any
from geo_data_points.base import BaseMeasurement
from geo_data_points.utils.html_parser import HTMLAnalyzer
from loguru import logger
import json
from datetime import datetime


class SchemaArticleMeasurement(BaseMeasurement):
    """Validate Article schema.org structured data."""

    def __init__(self):
        super().__init__(
            code="WI-014",
            name="Schema.org - Article",
            description="Validates Article schema.org structured data completeness and accuracy",
            category="Web Infrastructure",
            weight=0.80  # High value for content attribution
        )

    async def measure(self, url: str, html: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Measure Article schema quality.

        Scoring:
        - 100: Perfect article with all recommended fields (author, dates, publisher, image)
        - 85: Complete article with author, headline, datePublished
        - 70: Basic article with headline and datePublished
        - 50: Article present but missing critical fields
        - 0: No article schema

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
                # Check if page looks like article content
                html_lower = html.lower()
                has_article_indicators = any(word in html_lower for word in ['<article', 'blog', 'post', 'news'])

                if has_article_indicators:
                    return {
                        'score': 0,
                        'comment': 'Page appears to be an article but lacks Article schema. Add Article/NewsArticle/BlogPosting structured data for proper content attribution and AI extraction.'
                    }
                else:
                    return {
                        'score': 0,
                        'comment': 'No Article schema found. If page contains article content, add Article structured data.'
                    }

            # Find Article schemas (Article, NewsArticle, BlogPosting, TechArticle, etc.)
            article_types = ['Article', 'NewsArticle', 'BlogPosting', 'TechArticle', 'Report', 'ScholarlyArticle']
            article_schemas = []

            for script in json_ld_scripts:
                try:
                    data = json.loads(script) if isinstance(script, str) else script

                    # Handle both single object and array
                    if isinstance(data, list):
                        for item in data:
                            if item.get('@type') in article_types:
                                article_schemas.append(item)
                    elif data.get('@type') in article_types:
                        article_schemas.append(data)
                except:
                    continue

            if not article_schemas:
                return {
                    'score': 0,
                    'comment': f'No Article schema found. Add one of: {", ".join(article_types[:3])} structured data for content attribution.'
                }

            # Validate Article schemas (use first/best one)
            article = article_schemas[0]
            article_type = article.get('@type', 'Article')

            issues = []
            warnings = []
            score = 100

            # Required fields
            has_headline = 'headline' in article and article['headline'].strip()
            if not has_headline:
                issues.append('Missing required "headline" property')
                score -= 25

            # Strongly recommended fields
            has_author = 'author' in article
            if has_author:
                author = article['author']
                if isinstance(author, dict):
                    if '@type' not in author or 'name' not in author:
                        warnings.append('Author object missing @type or name')
                        score -= 5
            else:
                warnings.append('Missing "author" property - important for content attribution')
                score -= 15

            has_date_published = 'datePublished' in article
            if not has_date_published:
                warnings.append('Missing "datePublished" property - important for freshness signals')
                score -= 15
            else:
                # Validate date format
                try:
                    date_str = article['datePublished']
                    if 'T' in date_str:
                        parsed_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    else:
                        parsed_date = datetime.strptime(date_str, '%Y-%m-%d')
                except:
                    warnings.append('Invalid datePublished format (use ISO 8601)')
                    score -= 5

            has_date_modified = 'dateModified' in article
            if not has_date_modified:
                warnings.append('Consider adding "dateModified" for update tracking')
            else:
                # Validate date format
                try:
                    date_str = article['dateModified']
                    if 'T' in date_str:
                        parsed_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                except:
                    warnings.append('Invalid dateModified format (use ISO 8601)')

            has_publisher = 'publisher' in article
            if has_publisher:
                publisher = article['publisher']
                if isinstance(publisher, dict):
                    if '@type' not in publisher:
                        warnings.append('Publisher missing @type (should be Organization)')
                        score -= 3
                    if 'name' not in publisher:
                        warnings.append('Publisher missing name')
                        score -= 3
                    if 'logo' not in publisher:
                        warnings.append('Publisher missing logo')
                        score -= 3
            else:
                warnings.append('Missing "publisher" property - important for brand attribution')
                score -= 10

            has_image = 'image' in article
            if not has_image:
                warnings.append('Missing "image" property - recommended for visual representation')
                score -= 5

            # Optional but valuable fields
            has_description = 'description' in article or 'abstract' in article
            if has_description:
                score = min(100, score + 3)

            has_word_count = 'wordCount' in article
            if has_word_count:
                score = min(100, score + 2)

            has_article_body = 'articleBody' in article
            if has_article_body:
                body = article['articleBody']
                if len(body) < 100:
                    warnings.append('articleBody too short (<100 chars)')

            # Calculate final score
            score = max(0, score)

            # Generate comment
            if score >= 90:
                comment = f'{article_type} schema is excellent!'
            elif score >= 70:
                comment = f'{article_type} schema is good.'
            elif score >= 50:
                comment = f'{article_type} schema is present but needs improvement.'
            else:
                comment = f'{article_type} schema is incomplete.'

            # Add field summary
            present_fields = []
            if has_headline:
                present_fields.append('headline')
            if has_author:
                present_fields.append('author')
            if has_date_published:
                present_fields.append('datePublished')
            if has_publisher:
                present_fields.append('publisher')
            if has_image:
                present_fields.append('image')

            comment += f' Present: {", ".join(present_fields)}.'

            # Add issues and warnings
            if issues:
                comment += f' Critical issues: {"; ".join(issues)}.'
            if warnings and score < 100:
                comment += f' Improvements: {"; ".join(warnings[:2])}{"..." if len(warnings) > 2 else ""}.'

            return {
                'score': score,
                'comment': comment
            }

        except Exception as e:
            logger.error(f"Error measuring Article schema for {url}: {str(e)}")
            return {
                'score': 0,
                'comment': f'Measurement failed: {str(e)}'
            }


# Export for orchestrator
measurement = SchemaArticleMeasurement()
