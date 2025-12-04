"""
WI-007: Robots.txt - CCBot (CommonCrawl) Access Check

Validates if CCBot (CommonCrawl's crawler) has access to the site.
CommonCrawl data is used to train many LLMs, so blocking it affects AI training data.
"""

from typing import Dict, Any
from geo_data_points.base import BaseMeasurement
from geo_data_points.utils.http_client import CachedSession
from geo_data_points.utils.seo_helpers import RobotsTxtAnalyzer
from loguru import logger


class RobotsTxtCCBotMeasurement(BaseMeasurement):
    """Check if CCBot (CommonCrawl) has access to the site."""

    def __init__(self):
        super().__init__(
            code="WI-007",
            name="Robots.txt - CCBot Access",
            description="Validates CCBot access permissions in robots.txt",
            category="Web Infrastructure",
            weight=0.9  # Very high importance - CommonCrawl feeds many LLMs
        )
        self.session = CachedSession()

    async def measure(self, url: str, html: str = None, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Measure CCBot access permissions.

        Scoring:
        - 100: Explicitly allowed for CCBot
        - 75: Allowed via * user-agent (implicit)
        - 50: Partially blocked (some paths allowed)
        - 25: Mostly blocked
        - 0: Completely blocked or disallowed

        Args:
            url: Target URL to analyze
            html: Unused (robots.txt is fetched directly)
            metadata: Unused

        Returns:
            Dict with score (0-100) and detailed comment
        """
        try:
            # Extract domain from URL
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = f"{parsed.scheme}://{parsed.netloc}"
            robots_url = f"{domain}/robots.txt"

            # Fetch robots.txt
            response = self.session.get(robots_url)

            if response.status_code == 404:
                return {
                    'score': 75,
                    'comment': 'No robots.txt found - CCBot has implicit access (default allow). CommonCrawl can archive your content for LLM training. Consider adding robots.txt if you want control.'
                }

            if response.status_code != 200:
                return {
                    'score': 0,
                    'comment': f'Cannot access robots.txt (HTTP {response.status_code}). CCBot cannot determine access rules.'
                }

            # Parse robots.txt
            analyzer = RobotsTxtAnalyzer(response.text, domain)

            # Check specific CCBot user-agents
            ccbot_agents = [
                'CCBot',
                'CC-Bot',
                'CommonCrawl'
            ]

            # Check if CCBot is explicitly mentioned
            robots_lower = response.text.lower()
            explicitly_mentioned = any(
                agent.lower() in robots_lower
                for agent in ccbot_agents
            )

            if explicitly_mentioned:
                # Check if allowed or disallowed
                allowed_paths = []
                disallowed_paths = []

                lines = response.text.split('\n')
                current_agent = None

                for line in lines:
                    line = line.strip()
                    if line.startswith('User-agent:'):
                        agent = line.split(':', 1)[1].strip().lower()
                        current_agent = agent if any(
                            ca.lower() in agent for ca in ccbot_agents
                        ) else None
                    elif current_agent and line.lower().startswith('disallow:'):
                        path = line.split(':', 1)[1].strip()
                        disallowed_paths.append(path)
                    elif current_agent and line.lower().startswith('allow:'):
                        path = line.split(':', 1)[1].strip()
                        allowed_paths.append(path)

                # Calculate access level
                if disallowed_paths:
                    if '/' in disallowed_paths:
                        return {
                            'score': 0,
                            'comment': 'CCBot is explicitly blocked (Disallow: /). Your content will NOT be in CommonCrawl archives, limiting LLM training data exposure. This reduces GEO visibility significantly.'
                        }
                    else:
                        # Partial blocking
                        total_rules = len(disallowed_paths) + len(allowed_paths)
                        if total_rules > 0:
                            allowed_percentage = (len(allowed_paths) / total_rules) * 100
                            score = int(allowed_percentage)
                        else:
                            score = 50

                        return {
                            'score': score,
                            'comment': f'CCBot has partial access. {len(disallowed_paths)} paths blocked, {len(allowed_paths)} explicitly allowed. Blocked: {", ".join(disallowed_paths[:3])}{"..." if len(disallowed_paths) > 3 else ""}. Partial blocks reduce CommonCrawl coverage.'
                        }
                else:
                    return {
                        'score': 100,
                        'comment': f'CCBot is explicitly allowed. Excellent! Your content will be in CommonCrawl archives, maximizing LLM training data exposure. {len(allowed_paths) if allowed_paths else "All paths"} accessible.'
                    }

            else:
                # Not explicitly mentioned, check wildcard rules
                wildcard_check = analyzer.is_allowed('*', '/')

                if wildcard_check:
                    return {
                        'score': 75,
                        'comment': 'CCBot has implicit access via wildcard (*) user-agent rules. Your content will be in CommonCrawl. Consider adding explicit "User-agent: CCBot" + "Allow: /" for maximum clarity.'
                    }
                else:
                    # Check if wildcard blocks everything
                    lines = response.text.split('\n')
                    wildcard_disallow_all = False
                    in_wildcard = False

                    for line in lines:
                        line = line.strip()
                        if line.startswith('User-agent:'):
                            agent = line.split(':', 1)[1].strip()
                            in_wildcard = (agent == '*')
                        elif in_wildcard and line.lower().startswith('disallow:'):
                            path = line.split(':', 1)[1].strip()
                            if path == '/':
                                wildcard_disallow_all = True
                                break

                    if wildcard_disallow_all:
                        return {
                            'score': 0,
                            'comment': 'CCBot is blocked via wildcard (*) Disallow: / rule. Your content will NOT be in CommonCrawl archives, severely limiting LLM training data exposure and GEO visibility.'
                        }
                    else:
                        return {
                            'score': 75,
                            'comment': 'CCBot likely has access (no explicit block). Your content should be in CommonCrawl. Consider adding explicit "User-agent: CCBot" + "Allow: /" for certainty.'
                        }

        except Exception as e:
            logger.error(f"Error measuring CCBot access for {url}: {str(e)}")
            return {
                'score': 0,
                'comment': f'Measurement failed: {str(e)}'
            }


# Export for orchestrator
measurement = RobotsTxtCCBotMeasurement()
