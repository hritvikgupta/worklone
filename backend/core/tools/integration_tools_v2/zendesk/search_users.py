from typing import Any, Dict
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class ZendeskSearchUsersTool(BaseTool):
    name = "zendesk_search_users"
    description = "Search for users in Zendesk using a query string"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="ZENESDK_EMAIL",
                description="Your Zendesk email address",
                env_var="ZENESDK_EMAIL",
                required=True,
                auth_type="api_key",
            ),
            CredentialRequirement(
                key="ZENESDK_API_TOKEN",
                description="Zendesk API token",
                env_var="ZENESDK_API_TOKEN",
                required=True,
                auth_type="api_key",
            ),
            CredentialRequirement(
                key="ZENESDK_SUBDOMAIN",
                description="Your Zendesk subdomain",
                env_var="ZENESDK_SUBDOMAIN",
                required=True,
                auth_type="api_key",
            ),
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query string (e.g., user name or email)",
                },
                "externalId": {
                    "type": "string",
                    "description": "External ID to search by (your system identifier)",
                },
                "perPage": {
                    "type": "string",
                    "description": 'Results per page as a number string (default: "100", max: "100")',
                },
                "page": {
                    "type": "string",
                    "description": "Page number for pagination (1-based)",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        email = context.get("ZENESDK_EMAIL") if context else None
        api_token = context.get("ZENESDK_API_TOKEN") if context else None
        subdomain = context.get("ZENESDK_SUBDOMAIN") if context else None

        if (
            self._is_placeholder_token(email)
            or self._is_placeholder_token(api_token)
            or self._is_placeholder_token(subdomain)
        ):
            return ToolResult(success=False, output="", error="Zendesk credentials not configured.")

        credentials_str = f"{email}/token:{api_token}"
        auth_b64 = base64.b64encode(credentials_str.encode("utf-8")).decode("utf-8")
        headers = {
            "Authorization": f"Basic {auth_b64}",
            "Content-Type": "application/json",
        }

        url = f"https://{subdomain}.zendesk.com/api/v2/users/search.json"

        query_params: Dict[str, str] = {}
        query_val = parameters.get("query")
        if query_val:
            query_params["query"] = query_val
        external_id_val = parameters.get("externalId")
        if external_id_val:
            query_params["external_id"] = external_id_val
        per_page_val = parameters.get("perPage")
        if per_page_val:
            query_params["per_page"] = per_page_val
        page_val = parameters.get("page")
        if page_val:
            query_params["page"] = page_val

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")