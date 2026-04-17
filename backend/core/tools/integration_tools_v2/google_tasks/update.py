from typing import Any, Dict
import httpx
from urllib.parse import quote
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleTasksUpdateTool(BaseTool):
    name = "google_tasks_update"
    description = "Update an existing task in a Google Tasks list"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GOOGLE_TASKS_ACCESS_TOKEN",
                description="Google Tasks OAuth access token",
                env_var="GOOGLE_TASKS_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "google-tasks",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("GOOGLE_TASKS_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "taskListId": {
                    "type": "string",
                    "description": "Task list ID (defaults to primary task list \"@default\")",
                },
                "taskId": {
                    "type": "string",
                    "description": "The ID of the task to update",
                },
                "title": {
                    "type": "string",
                    "description": "New title for the task",
                },
                "notes": {
                    "type": "string",
                    "description": "New notes for the task",
                },
                "due": {
                    "type": "string",
                    "description": "New due date in RFC 3339 format",
                },
                "status": {
                    "type": "string",
                    "description": "New status: \"needsAction\" or \"completed\"",
                },
            },
            "required": ["taskId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        tasklist_id = parameters.get("taskListId", "@default")
        task_id = parameters["taskId"]
        body: Dict[str, Any] = {}
        for field in ("title", "notes", "due", "status"):
            if field in parameters:
                body[field] = parameters[field]
        
        url = f"https://tasks.googleapis.com/v1/lists/{quote(tasklist_id)}/tasks/{quote(task_id)}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")