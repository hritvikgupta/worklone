from typing import Any, Dict
import httpx
import urllib.parse
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleTasksDeleteTool(BaseTool):
    name = "google_tasks_delete"
    description = "Delete a task from a Google Tasks list"
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
                    "description": "The ID of the task to delete",
                },
            },
            "required": ["taskId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        task_list_id = parameters.get("taskListId", "@default")
        task_id = parameters["taskId"]
        
        url = f"https://tasks.googleapis.com/v1/lists/{urllib.parse.quote(task_list_id)}/tasks/{urllib.parse.quote(task_id)}"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)
                
                if response.status_code == 204:
                    return ToolResult(
                        success=True,
                        output="",
                        data={"taskId": task_id, "deleted": True},
                    )
                else:
                    error_msg = response.text
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("error", {}).get("message", error_msg)
                    except:
                        pass
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")