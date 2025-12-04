import requests
from requests.auth import HTTPBasicAuth
from app.core.config import settings


class JiraService:
    def __init__(self):
        self.base_url = settings.JIRA_BASE_URL
        self.email = settings.JIRA_EMAIL
        self.api_token = settings.JIRA_API_TOKEN

        if not all([self.base_url, self.email, self.api_token]):
            print("Warning: Jira credentials not configured")

    async def create_ticket(
        self,
        project_key: str,
        summary: str,
        description: str,
        priority: str = "medium"
    ) -> str:
        """
        Create a Jira ticket via REST API.
        """
        if not all([self.base_url, self.email, self.api_token]):
            # Mock mode for demo
            return f"MOCK-{project_key}-123"

        # Map severity to Jira priority
        priority_map = {
            "high": "Highest",
            "medium": "Medium",
            "low": "Low"
        }

        jira_priority = priority_map.get(priority, "Medium")

        url = f"{self.base_url}/rest/api/3/issue"
        auth = HTTPBasicAuth(self.email, self.api_token)
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        payload = {
            "fields": {
                "project": {
                    "key": project_key
                },
                "summary": summary,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": description
                                }
                            ]
                        }
                    ]
                },
                "issuetype": {
                    "name": "Task"
                },
                "priority": {
                    "name": jira_priority
                }
            }
        }

        try:
            response = requests.post(url, json=payload, headers=headers, auth=auth)
            response.raise_for_status()

            result = response.json()
            ticket_key = result.get("key", "UNKNOWN")
            return ticket_key

        except requests.exceptions.RequestException as e:
            print(f"Error creating Jira ticket: {str(e)}")
            # Return mock ticket ID on error
            return f"ERROR-{project_key}-000"
