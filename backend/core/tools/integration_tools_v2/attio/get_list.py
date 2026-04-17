from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class AttioGetListTool(BaseTool):
    name = "attio_get_list"
    description = "Get a single list by ID or slug"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="ATTIO_ACCESS_TOKEN",
                description="Attio access token",
                env_var="ATTIO_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "attio",
            context=context,
            context_token_keys=("access_token",),
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
                    "description": "The list ID or slug",
                },
            },
            "required": ["list"],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        
        list_id = (parameters.get("list") or "").strip()
        url = f"https://api.attio.com/v2/lists/{list_id}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code >= 400:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("message", "Failed to get list")
                    except Exception:
                        error_msg = response.text
                    return ToolResult(success=False, output="", error=error_msg)
                
                data = response.json()
                list_data = data.get("data", {})
                
                actor = list_data.get("created_by_actor")
                created_by_actor = None
                if actor:
                    created_by_actor = {
                        "type": actor.get("type"),
                        "id": actor.get("id"),
                    }
                
                parent_object = list_data.get("parent_object")
                if isinstance(parent_object, list):
                    parent_object = parent_object[0] if parent_object else None
                
                output_data = {
                    "listId": list_data.get("id", {}).get("list_id"),
                    "apiSlug": list_data.get("api_slug"),
                    "name": list_data.get("name"),
                    "parentObject": parent_object,
                    "workspaceAccess": list_data.get("workspace_access"),
                    "workspaceMemberAccess": list_data.get("workspace_member_access"),
                    "createdByActor": created_by_actor,
                    "createdAt": list_data.get("created_at"),
                }
                
                return ToolResult(success=True, output="List retrieved successfully.", data=output_data)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")