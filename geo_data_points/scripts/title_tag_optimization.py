"""
Title Tag Optimization Check

Checks title tag presence, length, and keyword usage.
Critical for GEO as title tags are heavily weighted in search results.

Module: SEO
Priority: High
Automation: Full
"""

from typing import Dict, Any
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from scripts.base_measurement import BaseMeasurement
from utils import fetch_url, parse_html


class TitleTagOptimization(BaseMeasurement):
    """
    Check title tag optimization.

    Score:
    - 100: Title present, optimal length (30-60 chars), descriptive
    - 75-99: Title present, good length (20-70 chars)
    - 50-74: Title present but suboptimal length
    - 25-49: Title present but very short/long
    - 0: No title tag
    """

    def measure(self) -> Dict[str, Any]:
        """
        Check title tag optimization.

        Returns:
            dict: Score and comment about title tag
        """
        response = fetch_url(self.url)
        if not response:
            return self._default_error_result("Failed to fetch URL")

        soup = parse_html(response.text)
        if not soup:
            return self._default_error_result("Failed to parse HTML")

        # Find title tag
        title_tag = soup.find('title')

        if not title_tag or not title_tag.string:
            return {
                'score': 0.0,
                'comment': 'No title tag found. ✗ Add a title tag - critical for GEO ranking.',
                'metadata': {
                    'title_present': False,
                    'recommendation': 'Add <title> tag with 30-60 characters, descriptive and keyword-rich.'
                }
            }

        title_text = title_tag.string.strip()
        title_length = len(title_text)

        # Score based on length
        # Optimal: 30-60 chars → 100
        # Good: 20-70 chars → 75-99
        # Acceptable: 15-80 chars → 50-74
        # Suboptimal: < 15 or > 80 chars → 25-49

        if 30 <= title_length <= 60:
            score = 100.0
            rating = "Optimal"
            comment = f'Title tag: "{title_text[:50]}..." ({title_length} chars). ✓ Optimal length for GEO.'
        elif 20 <= title_length <= 70:
            # Calculate score within range
            if title_length < 30:
                score = 75 + ((title_length - 20) / 10) * 25  # Scale from 75 to 100
            else:
                score = 100 - ((title_length - 60) / 10) * 25  # Scale from 100 to 75
            rating = "Good"
            comment = f'Title tag: "{title_text[:50]}..." ({title_length} chars). Good length, near optimal.'
        elif 15 <= title_length <= 80:
            if title_length < 20:
                score = 50 + ((title_length - 15) / 5) * 25
            else:
                score = 75 - ((title_length - 70) / 10) * 25
            rating = "Acceptable"
            comment = f'Title tag: "{title_text[:50]}..." ({title_length} chars). Acceptable, but consider optimizing to 30-60 chars.'
        elif title_length < 15:
            score = max(25, (title_length / 15) * 50)
            rating = "Too Short"
            comment = f'Title tag too short: "{title_text}" ({title_length} chars). ✗ Expand to 30-60 chars for better GEO.'
        else:  # > 80
            score = max(25, 50 - ((title_length - 80) / 20) * 25)
            rating = "Too Long"
            comment = f'Title tag too long: "{title_text[:50]}..." ({title_length} chars). ✗ Shorten to 30-60 chars for optimal GEO.'

        # Check for common issues
        issues = []
        if title_text.upper() == title_text and len(title_text) > 5:
            issues.append("All uppercase (poor readability)")
        if title_text.startswith(('Untitled', 'Home', 'Welcome')):
            issues.append("Generic title (not descriptive)")
        if '|' not in title_text and '-' not in title_text:
            issues.append("No brand separator (consider adding)")

        return {
            'score': round(score, 2),
            'comment': comment,
            'metadata': {
                'title_present': True,
                'title_text': title_text,
                'title_length': title_length,
                'rating': rating,
                'issues': issues,
                'recommendation': 'Aim for 30-60 characters, descriptive, keyword-rich, with brand separator.' if score < 100 else None
            }
        }


if __name__ == "__main__":
    import sys
    test_url = sys.argv[1] if len(sys.argv) > 1 else "https://anthropic.com"

    measurement = TitleTagOptimization(test_url)
    result = measurement.run()
    print(f"Score: {result['score']}")
    print(f"Comment: {result['comment']}")
    print(f"Title: {result['metadata'].get('title_text', 'N/A')}")
