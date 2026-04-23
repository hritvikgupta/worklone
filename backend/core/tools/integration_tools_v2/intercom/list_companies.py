from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class IntercomListCompaniesTool(BaseTool):
    name = "intercom_list_companies"
    description = "List all companies from Intercom with pagination support. Note: This endpoint has a limit of 10,000 companies that can be returned using pagination. For datasets larger than 10,000 companies, use the Scroll API instead."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="INTERCOM_ACCESS_TOKEN",
                description="Intercom API access token",
                env_var="INTERCOM_ACCESS_TOKEN",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "intercom",
            context=context,
            context_token_keys=("access_token",),
            env_token_keys=("INTERCOM_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "per_page": {
                    "type": "number",
                    "description": "Number of results per page",
                },
                "page": {
                    "type": "number",
                    "description": "Page number",
                },
                "starting_after": {
                    "type": "string",
                    "description": "Cursor for pagination (preferred over page-based pagination)",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Intercom-Version": "2.14",
        }
        
        url = "https://api.intercom.io/companies/list"
        query_params: dict[str, Any] = {}
        if "per_page" in parameters:
            query_params["per_page"] = parameters["per_page"]
        if "page" in parameters:
            query_params["page"] = parameters["page"]
        if "starting_after" in parameters:
            query_params["starting_after"] = parameters["starting_after"]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, params=query_params, json={})
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")