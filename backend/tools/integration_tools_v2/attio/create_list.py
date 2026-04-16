from typing import Any, Dict
import httpx
import json
import re
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class AttioCreateListTool(BaseTool):
    name = "attio_create_list"
    description = "Create a new list in Attio"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def _generate_api_slug(self, name: str) -> str:
        slug = re.sub(r'[^a-z0-9]+', '_', name.lower())
        return slug.strip('_')

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="ATTIO_ACCESS_TOKEN",
                description="Access token",
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
                "name": {
                    "type": "string",
                    "description": "The list name",
                },
                "apiSlug": {
                    "type": "string",
                    "description": "The API slug for the list (auto-generated from name if omitted)",
                },
                "parentObject": {
                    "type": "string",
                    "description": "The parent object slug (e.g. people, companies)",
                },
                "workspaceAccess": {
                    "type": "string",
                    "description": "Workspace-level access: full-access, read-and-write, or read-only (omit for private)",
                },
                "workspaceMemberAccess": {
                    "type": "string",
                    "description": "JSON array of member access entries, e.g. [{'workspace_member_id':'...','level':'read-and-write'}]",
                },
            },
            "required": ["name", "parentObject"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        name = parameters["name"]
        api_slug = parameters.get("apiSlug") or self._generate_api_slug(name)
        parent_object = parameters["parentObject"]
        workspace_access = parameters.get("workspaceAccess") or None
        wma = parameters.get("workspaceMemberAccess")
        workspace_member_access = []
        if wma:
            try:
                if isinstance(wma, str):
                    workspace_member_access = json.loads(wma)
                else:
                    workspace_member_access = wma
            except (json.JSONDecodeError, ValueError):
                workspace_member_access = wma
        
        data = {
            "name": name,
            "api_slug": api_slug,
            "parent_object": parent_object,
            "workspace_access": workspace_access,
            "workspace_member_access": workspace_member_access,
        }
        json_body = {"data": data}
        url = "https://api.attio.com/v2/lists"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=json_body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")