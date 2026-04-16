from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class HexListProjectsTool(BaseTool):
    name = "hex_list_projects"
    description = "List all projects in your Hex workspace with optional filtering by status."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="hex_api_key",
                description="Hex API token (Personal or Workspace)",
                env_var="HEX_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "hex",
            context=context,
            context_token_keys=("hex_api_key",),
            env_token_keys=("HEX_API_KEY",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "number",
                    "description": "Maximum number of projects to return (1-100)",
                },
                "includeArchived": {
                    "type": "boolean",
                    "description": "Include archived projects in results",
                },
                "statusFilter": {
                    "type": "string",
                    "description": "Filter by status: PUBLISHED, DRAFT, or ALL",
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
            "Content-Type": "application/json",
        }
        
        url = "https://app.hex.tech/api/v1/projects"
        params_dict: Dict[str, Any] = {}
        limit = parameters.get("limit")
        if limit is not None:
            params_dict["limit"] = limit
        include_archived = parameters.get("includeArchived")
        if include_archived is True:
            params_dict["includeArchived"] = "true"
        status_filter = parameters.get("statusFilter")
        if status_filter:
            params_dict["statuses[]"] = status_filter
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params_dict)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")