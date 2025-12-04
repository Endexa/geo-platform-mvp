"""
WI-009: Robots.txt - Bingbot Access Check

Validates if Bingbot (Microsoft Bing's crawler) has access to the site.
Bingbot data feeds Bing Search and Microsoft's Copilot/ChatGPT integration.
"""

from typing import Dict, Any
from geo_data_points.base import BaseMeasurement
from geo_data_points.utils.http_client import CachedSession
from geo_data_points.utils.seo_helpers import RobotsTxtAnalyzer
from loguru import logger


class RobotsTxtBingbotMeasurement(BaseMeasurement):
    """Check if Bingbot has access to the site."""

    def __init__(self):
        super().__init__(
            code="WI-009",
            name="Robots.txt - Bingbot Access",
            description="Validates Bingbot access permissions in robots.txt",
            category="Web Infrastructure",
            weight=0.85  # High importance - feeds Bing and Copilot
        )
        self.session = CachedSession()

    async def measure(self, url: str, html: str = None, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Measure Bingbot access permissions.

        Scoring:
        - 100: Explicitly allowed for Bingbot
        - 75: Allowed via * user-agent (implicit)
        - 50: Partially blocked
        - 0: Completely blocked

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
                    'comment': 'No robots.txt found - Bingbot has implicit access (default allow). Your content will be indexed by Bing and available to Copilot. Consider adding robots.txt for control.'
                }

            if response.status_code != 200:
                return {
                    'score': 0,
                    'comment': f'Cannot access robots.txt (HTTP {response.status_code}). Bingbot cannot determine access rules.'
                }

            # Parse robots.txt
            analyzer = RobotsTxtAnalyzer(response.text, domain)

            # Check specific Bingbot user-agents
            bingbot_agents = [
                'bingbot',
                'msnbot',  # Legacy Microsoft bot
                'BingPreview',  # Bing Preview bot
                'adidxbot'  # Bing Ads bot
            ]

            # Check if Bingbot is explicitly mentioned
            robots_lower = response.text.lower()
            explicitly_mentioned = any(
                agent.lower() in robots_lower
                for agent in bingbot_agents
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
                            ba.lower() in agent for ba in bingbot_agents
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
                            'comment': 'Bingbot is explicitly blocked (Disallow: /). Your content will NOT be indexed by Bing or available to Copilot/ChatGPT Bing integration. This eliminates GEO visibility in Microsoft AI ecosystem.'
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
                            'comment': f'Bingbot has partial access. {len(disallowed_paths)} paths blocked, {len(allowed_paths)} allowed. Blocked: {", ".join(disallowed_paths[:3])}{"..." if len(disallowed_paths) > 3 else ""}. Partial blocks reduce Bing/Copilot coverage.'
                        }
                else:
                    return {
                        'score': 100,
                        'comment': f'Bingbot is explicitly allowed. Excellent! Your content will be fully indexed by Bing and available to Copilot/ChatGPT Bing integration. {len(allowed_paths) if allowed_paths else "All paths"} accessible.'
                    }

            else:
                # Not explicitly mentioned, check wildcard rules
                wildcard_check = analyzer.is_allowed('*', '/')

                if wildcard_check:
                    return {
                        'score': 75,
                        'comment': 'Bingbot has implicit access via wildcard (*) user-agent rules. Your content will be indexed by Bing and available to Copilot. Consider adding explicit "User-agent: bingbot" + "Allow: /" for clarity.'
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
                            'comment': 'Bingbot is blocked via wildcard (*) Disallow: / rule. Your content will NOT be indexed by Bing or available to Copilot, eliminating GEO visibility in Microsoft AI ecosystem.'
                        }
                    else:
                        return {
                            'score': 75,
                            'comment': 'Bingbot likely has access (no explicit block). Your content should be indexed by Bing and available to Copilot. Consider adding explicit "User-agent: bingbot" + "Allow: /" for certainty.'
                        }

        except Exception as e:
            logger.error(f"Error measuring Bingbot access for {url}: {str(e)}")
            return {
                'score': 0,
                'comment': f'Measurement failed: {str(e)}'
            }


# Export for orchestrator
measurement = RobotsTxtBingbotMeasurement()
