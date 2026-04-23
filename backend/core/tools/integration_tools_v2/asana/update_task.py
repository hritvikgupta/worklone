from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class AsanaUpdateTaskTool(BaseTool):
    name = "asana_update_task"
    description = "Update an existing task in Asana"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="ASANA_ACCESS_TOKEN",
                description="OAuth access token for Asana",
                env_var="ASANA_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "asana",
            context=context,
            context_token_keys=("asana_token",),
            env_token_keys=("ASANA_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "taskGid": {
                    "type": "string",
                    "description": "Asana task GID (numeric string) of the task to update",
                },
                "name": {
                    "type": "string",
                    "description": "Updated name for the task",
                },
                "notes": {
                    "type": "string",
                    "description": "Updated notes or description for the task",
                },
                "assignee": {
                    "type": "string",
                    "description": "Updated assignee user GID",
                },
                "completed": {
                    "type": "boolean",
                    "description": "Mark task as completed or not completed",
                },
                "due_on": {
                    "type": "string",
                    "description": "Updated due date in YYYY-MM-DD format",
                },
            },
            "required": ["taskGid"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        task_gid = parameters.get("taskGid")
        if not task_gid:
            return ToolResult(success=False, output="", error="Task GID is required.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        
        url = f"https://app.asana.com/api/1.0/tasks/{task_gid}"
        
        task_data: dict[str, Any] = {}
        for field in ["name", "notes", "assignee", "completed", "due_on"]:
            if field in parameters:
                task_data[field] = parameters[field]
        
        body = {"data": task_data}
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.put(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")