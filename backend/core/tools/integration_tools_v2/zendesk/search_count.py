from typing import Any, Dict
import httpx
import base64
from urllib.parse import urlencode
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class ZendeskSearchCountTool(BaseTool):
    name = "zendesk_search_count"
    description = "Count the number of search results matching a query in Zendesk"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="ZENDESK_API_TOKEN",
                description="Zendesk API token",
                env_var="ZENDESK_API_TOKEN",
                required=True,
                auth_type="api_key",
            )
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "email": {
                    "type": "string",
                    "description": "Your Zendesk email address",
                },
                "apiToken": {
                    "type": "string",
                    "description": "Zendesk API token",
                },
                "subdomain": {
                    "type": "string",
                    "description": "Your Zendesk subdomain",
                },
                "query": {
                    "type": "string",
                    "description": 'Search query string using Zendesk search syntax (e.g., "type:ticket status:open")',
                },
            },
            "required": ["email", "apiToken", "subdomain", "query"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        email = parameters["email"]
        subdomain = parameters["subdomain"]
        query = parameters["query"]
        api_token = context.get("ZENDESK_API_TOKEN") if context else None
        if api_token is None:
            api_token = parameters.get("apiToken")
        if self._is_placeholder_token(api_token):
            return ToolResult(success=False, output="", error="Zendesk API token not configured.")

        credentials_str = f"{email}/token:{api_token}"
        base64_credentials = base64.b64encode(credentials_str.encode()).decode()
        headers = {
            "Authorization": f"Basic {base64_credentials}",
            "Content-Type": "application/json",
        }
        query_params = urlencode({"query": query})
        url = f"https://{subdomain}.zendesk.com/api/v2/search/count?{query_params}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")