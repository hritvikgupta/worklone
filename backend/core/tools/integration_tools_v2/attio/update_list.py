from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class AttioUpdateListTool(BaseTool):
    name = "attio_update_list"
    description = "Update a list in Attio"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="ATTIO_ACCESS_TOKEN",
                description="Access token for the Attio API",
                env_var="ATTIO_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "attio",
            context=context,
            context_token_keys=("provider_token",),
            env_token_keys=("ATTIO_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "list": {
                    "type": "string",
                    "description": "The list ID or slug to update",
                },
                "name": {
                    "type": "string",
                    "description": "New name for the list",
                },
                "apiSlug": {
                    "type": "string",
                    "description": "New API slug for the list",
                },
                "workspaceAccess": {
                    "type": "string",
                    "description": "New workspace-level access: full-access, read-and-write, or read-only (omit for private)",
                },
                "workspaceMemberAccess": {
                    "type": "string",
                    "description": "JSON array of member access entries, e.g. [{\"workspace_member_id\":\"...\",\"level\":\"read-and-write\"}]",
                },
            },
            "required": ["list"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = f"https://api.attio.com/v2/lists/{parameters['list'].strip()}"
        
        data: Dict[str, Any] = {}
        if parameters.get("name") is not None:
            data["name"] = parameters["name"]
        if parameters.get("apiSlug") is not None:
            data["api_slug"] = parameters["apiSlug"]
        if parameters.get("workspaceAccess") is not None:
            data["workspace_access"] = parameters["workspaceAccess"]
        if parameters.get("workspaceMemberAccess") is not None:
            wma = parameters["workspaceMemberAccess"]
            if isinstance(wma, str):
                try:
                    wma = json.loads(wma)
                except json.JSONDecodeError:
                    pass
            data["workspace_member_access"] = wma
        
        body = {"data": data}
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")