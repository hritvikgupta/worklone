from typing import Any, Dict
import httpx
import base64
import urllib.parse
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class ZendeskGetUsersTool(BaseTool):
    name = "zendesk_get_users"
    description = "Retrieve a list of users from Zendesk with optional filtering"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return []

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "email": {
                    "type": "string",
                    "description": "Your Zendesk email address"
                },
                "apiToken": {
                    "type": "string",
                    "description": "Zendesk API token"
                },
                "subdomain": {
                    "type": "string",
                    "description": "Your Zendesk subdomain (e.g., \"mycompany\" for mycompany.zendesk.com)"
                },
                "role": {
                    "type": "string",
                    "description": "Filter by role: \"end-user\", \"agent\", or \"admin\""
                },
                "permissionSet": {
                    "type": "string",
                    "description": "Filter by permission set ID as a numeric string (e.g., \"12345\")"
                },
                "perPage": {
                    "type": "string",
                    "description": "Results per page as a number string (default: \"100\", max: \"100\")"
                },
                "pageAfter": {
                    "type": "string",
                    "description": "Cursor from a previous response to fetch the next page of results"
                }
            },
            "required": ["email", "apiToken", "subdomain"]
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        email = parameters.get("email")
        api_token = parameters.get("apiToken")
        subdomain = parameters.get("subdomain")

        if self._is_placeholder_token(email) or self._is_placeholder_token(api_token) or self._is_placeholder_token(subdomain):
            return ToolResult(success=False, output="", error="Zendesk credentials not configured.")

        credentials_str = f"{email}/token:{api_token}"
        base64_credentials = base64.b64encode(credentials_str.encode("utf-8")).decode("utf-8")

        headers = {
            "Authorization": f"Basic {base64_credentials}",
            "Content-Type": "application/json",
        }

        query_dict: Dict[str, str] = {}
        role = parameters.get("role")
        if role:
            query_dict["role"] = role
        permission_set = parameters.get("permissionSet")
        if permission_set:
            query_dict["permission_set"] = permission_set
        per_page = parameters.get("perPage")
        if per_page:
            query_dict["per_page"] = per_page
        page_after = parameters.get("pageAfter")
        if page_after:
            query_dict["page_after"] = page_after

        query_string = urllib.parse.urlencode(query_dict)
        url = f"https://{subdomain}.zendesk.com/api/v2/users.json"
        if query_string:
            url += f"?{query_string}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")