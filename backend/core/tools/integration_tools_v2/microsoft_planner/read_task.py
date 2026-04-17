from typing import Any, Dict, List
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class MicrosoftPlannerReadTool(BaseTool):
    name = "microsoft_planner_read_task"
    description = "Read tasks from Microsoft Planner - get all user tasks or all tasks from a specific plan"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="MICROSOFT_PLANNER_ACCESS_TOKEN",
                description="Access token for the Microsoft Planner API",
                env_var="MICROSOFT_PLANNER_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "microsoft-planner",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("MICROSOFT_PLANNER_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "planId": {
                    "type": "string",
                    "description": "The ID of the plan to get tasks from, if not provided gets all user tasks (e.g., \"xqQg5FS2LkCe54tAMV_v2ZgADW2J\")",
                },
                "taskId": {
                    "type": "string",
                    "description": "The ID of the task to get (e.g., \"pbT5K2OVkkO1M7r5bfsJ6JgAGD5m\")",
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

        params = parameters
        url: str
        if "taskId" in params and params["taskId"]:
            clean_task_id = params["taskId"].strip()
            if not clean_task_id:
                return ToolResult(success=False, output="", error="Task ID cannot be empty")
            url = f"https://graph.microsoft.com/v1.0/planner/tasks/{clean_task_id}"
        elif "planId" in params and params["planId"]:
            clean_plan_id = params["planId"].strip()
            if not clean_plan_id:
                return ToolResult(success=False, output="", error="Plan ID cannot be empty")
            url = f"https://graph.microsoft.com/v1.0/planner/plans/{clean_plan_id}/tasks"
        else:
            url = "https://graph.microsoft.com/v1.0/me/planner/tasks"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    if isinstance(data, dict) and "value" in data:
                        raw_tasks = data["value"]
                    elif isinstance(data, list):
                        raw_tasks = data
                    else:
                        raw_tasks = [data]

                    tasks = []
                    for task in raw_tasks:
                        etag_value = task.get("@odata.etag")
                        if etag_value and isinstance(etag_value, str):
                            etag_value = etag_value.replace('\\"', '"')
                        task_dict = {
                            "id": task.get("id"),
                            "title": task.get("title"),
                            "planId": task.get("planId"),
                            "bucketId": task.get("bucketId"),
                            "percentComplete": task.get("percentComplete"),
                            "priority": task.get("priority"),
                            "dueDateTime": task.get("dueDateTime"),
                            "createdDateTime": task.get("createdDateTime"),
                            "completedDateTime": task.get("completedDateTime"),
                            "hasDescription": task.get("hasDescription"),
                            "assignments": list(task.get("assignments", {}).keys()) if task.get("assignments") else [],
                            "etag": etag_value,
                        }
                        tasks.append(task_dict)

                    user_id = None if data.get("value") is not None else "me"
                    metadata = {
                        "planId": tasks[0]["planId"] if tasks else None,
                        "userId": user_id,
                        "planUrl": f"https://graph.microsoft.com/v1.0/planner/plans/{tasks[0]['planId']}" if tasks else None,
                    }
                    transformed_output = {
                        "tasks": tasks,
                        "metadata": metadata,
                    }
                    return ToolResult(
                        success=True,
                        output=json.dumps(transformed_output),
                        data=transformed_output,
                    )
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")