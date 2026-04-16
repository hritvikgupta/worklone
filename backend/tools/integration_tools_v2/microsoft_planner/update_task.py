from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class MicrosoftPlannerUpdateTaskTool(BaseTool):
    name = "microsoft_planner_update_task"
    description = "Update a task in Microsoft Planner"
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

    def _clean_etag(self, etag: str) -> str:
        cleaned = etag.strip()
        while cleaned.startswith('"') and cleaned.endswith('"'):
            cleaned = cleaned[1:-1]
        if '\\\\"' in cleaned:
            cleaned = cleaned.replace('\\"', '"')
        return cleaned

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "taskId": {
                    "type": "string",
                    "description": "The ID of the task to update (e.g., \"pbT5K2OVkkO1M7r5bfsJ6JgAGD5m\")",
                },
                "etag": {
                    "type": "string",
                    "description": "The ETag value from the task to update (If-Match header)",
                },
                "title": {
                    "type": "string",
                    "description": "The new title of the task (e.g., \"Review quarterly report\")",
                },
                "bucketId": {
                    "type": "string",
                    "description": "The bucket ID to move the task to (e.g., \"hsOf2dhOJkC6Fey9VjDg1JgAC9Rq\")",
                },
                "dueDateTime": {
                    "type": "string",
                    "description": "The due date and time for the task in ISO 8601 format (e.g., \"2025-03-15T17:00:00Z\")",
                },
                "startDateTime": {
                    "type": "string",
                    "description": "The start date and time for the task (ISO 8601 format)",
                },
                "percentComplete": {
                    "type": "number",
                    "description": "The percentage of task completion (0-100)",
                },
                "priority": {
                    "type": "number",
                    "description": "The priority of the task (0-10)",
                },
                "assigneeUserId": {
                    "type": "string",
                    "description": "The user ID to assign the task to (e.g., \"e82f74c3-4d8a-4b5c-9f1e-2a6b8c9d0e3f\")",
                },
            },
            "required": ["taskId", "etag"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        task_id = parameters.get("taskId")
        if not task_id:
            return ToolResult(success=False, output="", error="Task ID is required")
        
        etag = parameters.get("etag")
        if not etag:
            return ToolResult(success=False, output="", error="ETag is required for update operations")
        
        cleaned_etag = self._clean_etag(etag)
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "If-Match": cleaned_etag,
        }
        
        body: Dict[str, Any] = {}
        title = parameters.get("title")
        if title is not None and title != "":
            body["title"] = title
        
        bucket_id = parameters.get("bucketId")
        if bucket_id is not None and bucket_id != "":
            body["bucketId"] = bucket_id
        
        due_date_time = parameters.get("dueDateTime")
        if due_date_time is not None and due_date_time != "":
            body["dueDateTime"] = due_date_time
        
        start_date_time = parameters.get("startDateTime")
        if start_date_time is not None and start_date_time != "":
            body["startDateTime"] = start_date_time
        
        percent_complete = parameters.get("percentComplete")
        if percent_complete is not None:
            body["percentComplete"] = percent_complete
        
        priority = parameters.get("priority")
        if priority is not None:
            body["priority"] = float(priority)
        
        assignee_user_id = parameters.get("assigneeUserId")
        if assignee_user_id is not None and assignee_user_id != "":
            body["assignments"] = {
                assignee_user_id: {
                    "@odata.type": "microsoft.graph.plannerAssignment",
                    "orderHint": " !",
                }
            }
        
        if not body:
            return ToolResult(success=False, output="", error="At least one field must be provided to update")
        
        url = f"https://graph.microsoft.com/v1.0/planner/tasks/{task_id}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    try:
                        data = response.json()
                    except:
                        data = None
                    return ToolResult(success=True, output=response.text, data=data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")