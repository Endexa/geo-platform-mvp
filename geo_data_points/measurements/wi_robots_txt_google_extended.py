"""
WI-008: Robots.txt - Google-Extended Access Check

Validates if Google-Extended (used for Bard/Gemini training) has access to the site.
Google-Extended allows publishers to control if their content is used for Generative AI training.
"""

from typing import Dict, Any
from geo_data_points.base import BaseMeasurement
from geo_data_points.utils.http_client import CachedSession
from geo_data_points.utils.seo_helpers import RobotsTxtAnalyzer
from loguru import logger


class RobotsTxtGoogleExtendedMeasurement(BaseMeasurement):
    """Check if Google-Extended has access to the site."""

    def __init__(self):
        super().__init__(
            code="WI-008",
            name="Robots.txt - Google-Extended Access",
            description="Validates Google-Extended access permissions in robots.txt",
            category="Web Infrastructure",
            weight=0.95  # Critical for Bard/Gemini indexing
        )
        self.session = CachedSession()

    async def measure(self, url: str, html: str = None, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Measure Google-Extended access permissions.

        Scoring:
        - 100: Explicitly allowed for Google-Extended
        - 75: Allowed via * user-agent (implicit)
        - 50: Partially blocked
        - 0: Completely blocked

        Note: Google-Extended is separate from Googlebot. Blocking Google-Extended
        does NOT affect Google Search rankings, only Bard/Gemini training.

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
                    'comment': 'No robots.txt found - Google-Extended has implicit access (default allow). Your content can be used for Bard/Gemini training. Add robots.txt to control this.'
                }

            if response.status_code != 200:
                return {
                    'score': 0,
                    'comment': f'Cannot access robots.txt (HTTP {response.status_code}). Google-Extended cannot determine access rules.'
                }

            # Parse robots.txt
            analyzer = RobotsTxtAnalyzer(response.text, domain)

            # Check specific Google-Extended user-agent
            google_extended_agents = [
                'Google-Extended',
                'GoogleExtended'
            ]

            # Check if Google-Extended is explicitly mentioned
            robots_lower = response.text.lower()
            explicitly_mentioned = any(
                agent.lower().replace('-', '').replace('_', '') in robots_lower.replace('-', '').replace('_', '')
                for agent in google_extended_agents
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
                        agent = line.split(':', 1)[1].strip().lower().replace('-', '').replace('_', '')
                        current_agent = agent if any(
                            ga.lower().replace('-', '').replace('_', '') in agent
                            for ga in google_extended_agents
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
                            'comment': 'Google-Extended is explicitly blocked (Disallow: /). Your content will NOT be used for Bard/Gemini training. This severely limits GEO visibility in Google\'s AI products. Note: This does NOT affect Google Search rankings.'
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
                            'comment': f'Google-Extended has partial access. {len(disallowed_paths)} paths blocked, {len(allowed_paths)} allowed. Blocked: {", ".join(disallowed_paths[:3])}{"..." if len(disallowed_paths) > 3 else ""}. Partial blocks reduce Bard/Gemini training data.'
                        }
                else:
                    return {
                        'score': 100,
                        'comment': f'Google-Extended is explicitly allowed. Perfect! Your content will be used for Bard/Gemini training, maximizing GEO visibility in Google\'s AI products. {len(allowed_paths) if allowed_paths else "All paths"} accessible.'
                    }

            else:
                # Not explicitly mentioned, check wildcard rules
                wildcard_check = analyzer.is_allowed('*', '/')

                if wildcard_check:
                    return {
                        'score': 75,
                        'comment': 'Google-Extended has implicit access via wildcard (*) user-agent rules. Your content can be used for Bard/Gemini training. Consider adding explicit "User-agent: Google-Extended" + "Allow: /" for maximum clarity and control.'
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
                            'comment': 'Google-Extended is blocked via wildcard (*) Disallow: / rule. Your content will NOT be used for Bard/Gemini training, severely limiting GEO visibility in Google\'s AI products.'
                        }
                    else:
                        return {
                            'score': 75,
                            'comment': 'Google-Extended likely has access (no explicit block). Your content should be used for Bard/Gemini training. Consider adding explicit "User-agent: Google-Extended" + "Allow: /" for certainty and control.'
                        }

        except Exception as e:
            logger.error(f"Error measuring Google-Extended access for {url}: {str(e)}")
            return {
                'score': 0,
                'comment': f'Measurement failed: {str(e)}'
            }


# Export for orchestrator
measurement = RobotsTxtGoogleExtendedMeasurement()
