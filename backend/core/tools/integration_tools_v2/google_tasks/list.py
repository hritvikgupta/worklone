from typing import Any, Dict
import httpx
import urllib.parse
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleTasksListTool(BaseTool):
    name = "google_tasks_list"
    description = "List all tasks in a Google Tasks list"
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
                "maxResults": {
                    "type": "number",
                    "description": "Maximum number of tasks to return (default 20, max 100)",
                },
                "pageToken": {
                    "type": "string",
                    "description": "Token for pagination",
                },
                "showCompleted": {
                    "type": "boolean",
                    "description": "Whether to show completed tasks (default true)",
                },
                "showDeleted": {
                    "type": "boolean",
                    "description": "Whether to show deleted tasks (default false)",
                },
                "showHidden": {
                    "type": "boolean",
                    "description": "Whether to show hidden tasks (default false)",
                },
                "dueMin": {
                    "type": "string",
                    "description": "Lower bound for due date filter (RFC 3339 timestamp)",
                },
                "dueMax": {
                    "type": "string",
                    "description": "Upper bound for due date filter (RFC 3339 timestamp)",
                },
                "completedMin": {
                    "type": "string",
                    "description": "Lower bound for task completion date (RFC 3339 timestamp)",
                },
                "completedMax": {
                    "type": "string",
                    "description": "Upper bound for task completion date (RFC 3339 timestamp)",
                },
                "updatedMin": {
                    "type": "string",
                    "description": "Lower bound for last modification time (RFC 3339 timestamp)",
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
        }
        
        tasklist_id = parameters.get("taskListId", "@default")
        base_url = "https://tasks.googleapis.com/v1"
        url = f"{base_url}/lists/{urllib.parse.quote(tasklist_id)}/tasks"
        
        query_params = {}
        if "maxResults" in parameters:
            query_params["maxResults"] = str(parameters["maxResults"])
        if "pageToken" in parameters:
            query_params["pageToken"] = parameters["pageToken"]
        if "showCompleted" in parameters:
            query_params["showCompleted"] = "true" if parameters["showCompleted"] else "false"
        if "showDeleted" in parameters:
            query_params["showDeleted"] = "true" if parameters["showDeleted"] else "false"
        if "showHidden" in parameters:
            query_params["showHidden"] = "true" if parameters["showHidden"] else "false"
        if "dueMin" in parameters:
            query_params["dueMin"] = parameters["dueMin"]
        if "dueMax" in parameters:
            query_params["dueMax"] = parameters["dueMax"]
        if "completedMin" in parameters:
            query_params["completedMin"] = parameters["completedMin"]
        if "completedMax" in parameters:
            query_params["completedMax"] = parameters["completedMax"]
        if "updatedMin" in parameters:
            query_params["updatedMin"] = parameters["updatedMin"]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")