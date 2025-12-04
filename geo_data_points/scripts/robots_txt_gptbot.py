"""
Robots.txt - GPTBot Check

Checks if GPTBot (OpenAI) is allowed to crawl the site.
Critical for ChatGPT visibility.

Module: WI (Web Infrastructure)
Priority: High
Automation: Full
"""

from urllib.robotparser import RobotFileParser
from typing import Dict, Any
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from scripts.base_measurement import BaseMeasurement
from utils import get_base_url


class RobotsTxtGPTBot(BaseMeasurement):
    """
    Check if GPTBot is allowed in robots.txt.

    Score:
    - 100: GPTBot explicitly allowed or no restriction
    - 50: No robots.txt found (default allow)
    - 0: GPTBot explicitly blocked
    """

    def measure(self) -> Dict[str, Any]:
        """
        Check robots.txt for GPTBot access.

        Returns:
            dict: Score and comment about GPTBot access
        """
        base_url = get_base_url(self.url)
        robots_url = f"{base_url}/robots.txt"

        try:
            rp = RobotFileParser()
            rp.set_url(robots_url)
            rp.read()

            # Check if GPTBot can fetch any path
            can_fetch = rp.can_fetch("GPTBot", self.url)

            if can_fetch:
                return {
                    'score': 100.0,
                    'comment': 'GPTBot is allowed to crawl this site. ✓ Optimal for ChatGPT visibility.',
                    'metadata': {
                        'robots_url': robots_url,
                        'user_agent': 'GPTBot',
                        'allowed': True
                    }
                }
            else:
                return {
                    'score': 0.0,
                    'comment': 'GPTBot is blocked in robots.txt. ✗ This prevents ChatGPT from accessing your content.',
                    'metadata': {
                        'robots_url': robots_url,
                        'user_agent': 'GPTBot',
                        'allowed': False,
                        'recommendation': 'Remove GPTBot from Disallow directives to improve GEO visibility.'
                    }
                }

        except Exception as e:
            # No robots.txt or parsing error = default allow
            return {
                'score': 50.0,
                'comment': f'No robots.txt found or parsing error. Default: GPTBot allowed. Consider adding explicit rules.',
                'metadata': {
                    'robots_url': robots_url,
                    'error': str(e),
                    'default_behavior': 'allow'
                }
            }


if __name__ == "__main__":
    # Test with known URLs
    test_urls = [
        "https://anthropic.com",
        "https://example.com"
    ]

    for url in test_urls:
        print(f"\nTesting {url}:")
        measurement = RobotsTxtGPTBot(url)
        result = measurement.run()
        print(f"Score: {result['score']}")
        print(f"Comment: {result['comment']}")
