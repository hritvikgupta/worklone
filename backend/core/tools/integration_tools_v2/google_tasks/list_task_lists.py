from typing import Any, Dict
import httpx
import json
from urllib.parse import urlencode
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleTasksListTaskListsTool(BaseTool):
    name = "google_tasks_list_task_lists"
    description = "Retrieve all task lists for the authenticated user"
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
                "maxResults": {
                    "type": "number",
                    "description": "Maximum number of task lists to return (default 20, max 100)",
                },
                "pageToken": {
                    "type": "string",
                    "description": "Token for pagination",
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
        
        query_params: dict[str, Any] = {}
        max_results = parameters.get("maxResults")
        if max_results is not None:
            query_params["maxResults"] = max_results
        page_token = parameters.get("pageToken")
        if page_token:
            query_params["pageToken"] = page_token
        
        url = "https://tasks.googleapis.com/tasks/v1/users/@me/lists"
        if query_params:
            url += "?" + urlencode(query_params)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    items = data.get("items", [])
                    task_lists = [
                        {
                            "id": item.get("id"),
                            "title": item.get("title"),
                            "updated": item.get("updated"),
                            "selfLink": item.get("selfLink"),
                        }
                        for item in items
                    ]
                    output_data = {
                        "taskLists": task_lists,
                        "nextPageToken": data.get("nextPageToken"),
                    }
                    return ToolResult(
                        success=True, output=json.dumps(output_data), data=output_data
                    )
                else:
                    try:
                        error_data = response.json()
                        error_msg = (
                            error_data.get("error", {}).get("message")
                            or "Failed to list task lists"
                        )
                    except Exception:
                        error_msg = response.text or "Failed to list task lists"
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")