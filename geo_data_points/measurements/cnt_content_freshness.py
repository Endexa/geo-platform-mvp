"""
CNT-003: Content Freshness

Measures content freshness based on dateModified, datePublished, and content update signals.
Fresh content is prioritized by AI models for current information retrieval.
"""

from typing import Dict, Any
from geo_data_points.base import BaseMeasurement
from geo_data_points.utils.html_parser import HTMLAnalyzer
from datetime import datetime, timedelta
from loguru import logger
import json
import re


class ContentFreshnessMeasurement(BaseMeasurement):
    """Measure content freshness based on publication and modification dates."""

    def __init__(self):
        super().__init__(
            code="CNT-003",
            name="Content Freshness",
            description="Measures content freshness based on publication/modification dates and update signals",
            category="Content",
            weight=0.95  # Critical for AI model preference
        )

    async def measure(self, url: str, html: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Measure content freshness.

        Scoring:
        - 100: Updated within last 7 days
        - 95: Updated within last 30 days
        - 85: Updated within last 90 days
        - 75: Updated within last 180 days
        - 60: Updated within last 365 days
        - 40: 1-2 years old
        - 20: 2-3 years old
        - 10: >3 years old
        - 0: No date information found

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

            # Strategy 1: Check JSON-LD Article schema for dates
            most_recent_date = None
            date_source = None

            json_ld_scripts = analyzer.get_json_ld()
            if json_ld_scripts:
                for script in json_ld_scripts:
                    try:
                        data = json.loads(script) if isinstance(script, str) else script

                        if isinstance(data, list):
                            data = data[0]

                        # Look for Article types
                        if data.get('@type') in ['Article', 'NewsArticle', 'BlogPosting', 'TechArticle']:
                            # Prefer dateModified over datePublished
                            if 'dateModified' in data:
                                try:
                                    date_str = data['dateModified']
                                    if 'T' in date_str:
                                        parsed = datetime.fromisoformat(date_str.replace('Z', '+00:00')).replace(tzinfo=None)
                                    else:
                                        parsed = datetime.strptime(date_str, '%Y-%m-%d')

                                    if most_recent_date is None or parsed > most_recent_date:
                                        most_recent_date = parsed
                                        date_source = 'JSON-LD dateModified'
                                except:
                                    pass

                            if 'datePublished' in data and most_recent_date is None:
                                try:
                                    date_str = data['datePublished']
                                    if 'T' in date_str:
                                        parsed = datetime.fromisoformat(date_str.replace('Z', '+00:00')).replace(tzinfo=None)
                                    else:
                                        parsed = datetime.strptime(date_str, '%Y-%m-%d')

                                    if most_recent_date is None or parsed > most_recent_date:
                                        most_recent_date = parsed
                                        date_source = 'JSON-LD datePublished'
                                except:
                                    pass
                    except:
                        continue

            # Strategy 2: Check meta tags
            if most_recent_date is None:
                meta_tags = analyzer.get_meta_tags()

                date_meta_keys = [
                    'article:modified_time',
                    'article:published_time',
                    'og:updated_time',
                    'last-modified',
                    'date'
                ]

                for key in date_meta_keys:
                    if key in meta_tags:
                        try:
                            date_str = meta_tags[key]
                            if 'T' in date_str:
                                parsed = datetime.fromisoformat(date_str.replace('Z', '+00:00')).replace(tzinfo=None)
                            else:
                                parsed = datetime.strptime(date_str, '%Y-%m-%d')

                            if most_recent_date is None or parsed > most_recent_date:
                                most_recent_date = parsed
                                date_source = f'Meta tag: {key}'
                            break
                        except:
                            continue

            # Strategy 3: Look for date patterns in HTML content
            if most_recent_date is None:
                # Look for common date patterns
                date_patterns = [
                    r'(\d{4})-(\d{2})-(\d{2})',  # 2024-12-04
                    r'(\d{2})/(\d{2})/(\d{4})',  # 12/04/2024
                    r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* (\d{1,2}),? (\d{4})'  # Dec 4, 2024
                ]

                for pattern in date_patterns:
                    matches = re.findall(pattern, html[:5000])  # Check first 5000 chars
                    if matches:
                        try:
                            match = matches[0]
                            if len(match) == 3:
                                if '-' in html[:5000]:
                                    parsed = datetime(int(match[0]), int(match[1]), int(match[2]))
                                    most_recent_date = parsed
                                    date_source = 'HTML content pattern'
                                    break
                        except:
                            pass

            if most_recent_date is None:
                return {
                    'score': 0,
                    'comment': 'No date information found. Add dateModified/datePublished in Article schema or meta tags to signal content freshness to AI models.'
                }

            # Calculate age
            now = datetime.utcnow()
            age_days = (now - most_recent_date).days

            # Determine score
            if age_days < 0:
                # Future date - likely error
                return {
                    'score': 0,
                    'comment': f'Invalid date detected (future date: {most_recent_date.strftime("%Y-%m-%d")}). Ensure correct date formatting.'
                }
            elif age_days <= 7:
                score = 100
                freshness = "Very Fresh"
                comment = f'{freshness}: Content updated {age_days} day(s) ago. Excellent for AI model prioritization!'
            elif age_days <= 30:
                score = 95
                freshness = "Fresh"
                comment = f'{freshness}: Content updated {age_days} days ago. Great for current information retrieval!'
            elif age_days <= 90:
                score = 85
                freshness = "Recent"
                comment = f'{freshness}: Content updated {age_days} days ago (3 months). Good freshness for most topics.'
            elif age_days <= 180:
                score = 75
                freshness = "Moderately Recent"
                comment = f'{freshness}: Content updated {age_days} days ago (6 months). Consider updating for better AI visibility.'
            elif age_days <= 365:
                score = 60
                freshness = "Aging"
                comment = f'{freshness}: Content updated {age_days} days ago (1 year). Update soon to maintain AI model preference.'
            elif age_days <= 730:
                score = 40
                freshness = "Stale"
                comment = f'{freshness}: Content updated {age_days} days ago (2 years). Update urgently - AI models deprioritize old content.'
            elif age_days <= 1095:
                score = 20
                freshness = "Very Stale"
                comment = f'{freshness}: Content updated {age_days} days ago (3 years). Critical update needed - AI models will skip outdated content.'
            else:
                score = 10
                freshness = "Outdated"
                comment = f'{freshness}: Content updated {age_days} days ago (>{age_days // 365} years). Severely outdated - AI models will ignore.'

            # Add date source info
            comment += f' Date source: {date_source}. Last update: {most_recent_date.strftime("%Y-%m-%d")}.'

            # Recommendations based on content type
            if age_days > 90:
                comment += ' Recommendation: Update content regularly and set dateModified in schema to signal freshness.'

            return {
                'score': score,
                'comment': comment
            }

        except Exception as e:
            logger.error(f"Error measuring content freshness for {url}: {str(e)}")
            return {
                'score': 0,
                'comment': f'Measurement failed: {str(e)}'
            }


# Export for orchestrator
measurement = ContentFreshnessMeasurement()
