"""
Robots.txt - ClaudeBot Check

Checks if ClaudeBot (Anthropic) is allowed to crawl the site.
Critical for Claude.ai visibility.

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


class RobotsTxtClaudeBot(BaseMeasurement):
    """
    Check if ClaudeBot is allowed in robots.txt.

    Score:
    - 100: ClaudeBot explicitly allowed or no restriction
    - 50: No robots.txt found (default allow)
    - 0: ClaudeBot explicitly blocked
    """

    def measure(self) -> Dict[str, Any]:
        """
        Check robots.txt for ClaudeBot access.

        Returns:
            dict: Score and comment about ClaudeBot access
        """
        base_url = get_base_url(self.url)
        robots_url = f"{base_url}/robots.txt"

        try:
            rp = RobotFileParser()
            rp.set_url(robots_url)
            rp.read()

            # Check if ClaudeBot can fetch any path
            can_fetch = rp.can_fetch("ClaudeBot", self.url)

            if can_fetch:
                return {
                    'score': 100.0,
                    'comment': 'ClaudeBot is allowed to crawl this site. ✓ Optimal for Claude.ai visibility.',
                    'metadata': {
                        'robots_url': robots_url,
                        'user_agent': 'ClaudeBot',
                        'allowed': True
                    }
                }
            else:
                return {
                    'score': 0.0,
                    'comment': 'ClaudeBot is blocked in robots.txt. ✗ This prevents Claude from accessing your content.',
                    'metadata': {
                        'robots_url': robots_url,
                        'user_agent': 'ClaudeBot',
                        'allowed': False,
                        'recommendation': 'Remove ClaudeBot from Disallow directives to improve GEO visibility.'
                    }
                }

        except Exception as e:
            # No robots.txt or parsing error = default allow
            return {
                'score': 50.0,
                'comment': f'No robots.txt found or parsing error. Default: ClaudeBot allowed. Consider adding explicit rules.',
                'metadata': {
                    'robots_url': robots_url,
                    'error': str(e),
                    'default_behavior': 'allow'
                }
            }


if __name__ == "__main__":
    import sys
    test_url = sys.argv[1] if len(sys.argv) > 1 else "https://anthropic.com"

    measurement = RobotsTxtClaudeBot(test_url)
    result = measurement.run()
    print(f"Score: {result['score']}")
    print(f"Comment: {result['comment']}")
