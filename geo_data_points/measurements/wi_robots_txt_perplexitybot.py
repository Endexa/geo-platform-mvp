"""
WI-006: Robots.txt - PerplexityBot Access Check

Validates if PerplexityBot (Perplexity AI's crawler) has access to the site.
Checks for explicit Allow/Disallow rules for PerplexityBot user-agent.
"""

from typing import Dict, Any
from geo_data_points.base import BaseMeasurement
from geo_data_points.utils.http_client import CachedSession
from geo_data_points.utils.seo_helpers import RobotsTxtAnalyzer
from loguru import logger


class RobotsTxtPerplexityBotMeasurement(BaseMeasurement):
    """Check if PerplexityBot has access to the site."""

    def __init__(self):
        super().__init__(
            code="WI-006",
            name="Robots.txt - PerplexityBot Access",
            description="Validates PerplexityBot access permissions in robots.txt",
            category="Web Infrastructure",
            weight=0.8  # High importance for Perplexity AI indexing
        )
        self.session = CachedSession()

    async def measure(self, url: str, html: str = None, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Measure PerplexityBot access permissions.

        Scoring:
        - 100: Explicitly allowed for PerplexityBot
        - 75: Allowed via * user-agent (implicit)
        - 50: Partially blocked (some paths allowed)
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
                    'comment': 'No robots.txt found - PerplexityBot has implicit access (default allow). Consider adding robots.txt for better control.'
                }

            if response.status_code != 200:
                return {
                    'score': 0,
                    'comment': f'Cannot access robots.txt (HTTP {response.status_code}). PerplexityBot cannot determine access rules.'
                }

            # Parse robots.txt
            analyzer = RobotsTxtAnalyzer(response.text, domain)

            # Check specific PerplexityBot user-agents
            perplexity_agents = [
                'PerplexityBot',
                'Perplexity',
                'PerplexityBot-Images',
                'PerplexityBot-Web'
            ]

            # Check if any PerplexityBot agent is explicitly mentioned
            robots_lower = response.text.lower()
            explicitly_mentioned = any(
                agent.lower() in robots_lower
                for agent in perplexity_agents
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
                            pa.lower() in agent for pa in perplexity_agents
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
                            'comment': f'PerplexityBot is explicitly blocked (Disallow: /). This prevents Perplexity AI from indexing your content. Blocked paths: {len(disallowed_paths)}'
                        }
                    else:
                        blocked_percentage = (len(disallowed_paths) / (len(disallowed_paths) + len(allowed_paths) + 1)) * 100
                        score = max(0, 100 - int(blocked_percentage))
                        return {
                            'score': score,
                            'comment': f'PerplexityBot has partial access. {len(disallowed_paths)} paths blocked, {len(allowed_paths)} explicitly allowed. Blocked paths: {", ".join(disallowed_paths[:3])}{"..." if len(disallowed_paths) > 3 else ""}'
                        }
                else:
                    return {
                        'score': 100,
                        'comment': f'PerplexityBot is explicitly allowed. Excellent for Perplexity AI indexing and citation. {len(allowed_paths)} paths explicitly allowed.'
                    }

            else:
                # Not explicitly mentioned, check wildcard rules
                wildcard_check = analyzer.is_allowed('*', '/')

                if wildcard_check:
                    return {
                        'score': 75,
                        'comment': 'PerplexityBot has implicit access via wildcard (*) user-agent rules. Consider adding explicit "User-agent: PerplexityBot" for better control.'
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
                            'comment': 'PerplexityBot is blocked via wildcard (*) Disallow: / rule. This prevents Perplexity AI from indexing your content.'
                        }
                    else:
                        return {
                            'score': 75,
                            'comment': 'PerplexityBot likely has access (no explicit block). Consider adding explicit "User-agent: PerplexityBot" with "Allow: /" for clarity.'
                        }

        except Exception as e:
            logger.error(f"Error measuring PerplexityBot access for {url}: {str(e)}")
            return {
                'score': 0,
                'comment': f'Measurement failed: {str(e)}'
            }


# Export for orchestrator
measurement = RobotsTxtPerplexityBotMeasurement()
