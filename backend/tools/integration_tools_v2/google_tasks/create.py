from typing import Any, Dict
import httpx
from urllib.parse import quote, urlencode
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleTasksCreateTool(BaseTool):
    name = "google_tasks_create"
    description = "Create a new task in a Google Tasks list"
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
                "title": {
                    "type": "string",
                    "description": "Title of the task (max 1024 characters)",
                },
                "notes": {
                    "type": "string",
                    "description": "Notes/description for the task (max 8192 characters)",
                },
                "due": {
                    "type": "string",
                    "description": "Due date in RFC 3339 format (e.g., 2025-06-03T00:00:00.000Z)",
                },
                "status": {
                    "type": "string",
                    "description": "Task status: \"needsAction\" or \"completed\"",
                },
                "parent": {
                    "type": "string",
                    "description": "Parent task ID to create this task as a subtask. Omit for top-level tasks.",
                },
                "previous": {
                    "type": "string",
                    "description": "Previous sibling task ID to position after. Omit to place first among siblings.",
                },
            },
            "required": ["title"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        task_list_id = parameters.get("taskListId", "@default")
        query_params = {}
        parent = parameters.get("parent")
        if parent:
            query_params["parent"] = parent
        previous = parameters.get("previous")
        if previous:
            query_params["previous"] = previous
        qs = urlencode(query_params) if query_params else ""
        url = f"https://tasks.googleapis.com/v1/lists/{quote(task_list_id)}/tasks"
        if qs:
            url += f"?{qs}"

        body = {
            "title": parameters["title"],
        }
        notes = parameters.get("notes")
        if notes:
            body["notes"] = notes
        due = parameters.get("due")
        if due:
            body["due"] = due
        status = parameters.get("status")
        if status:
            body["status"] = status

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")