from typing import Any, Dict, List
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class AttioListTasksTool(BaseTool):
    name = "attio_list_tasks"
    description = "List tasks in Attio, optionally filtered by record, assignee, or completion status"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="ATTIO_ACCESS_TOKEN",
                description="The OAuth access token for the Attio API",
                env_var="ATTIO_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "attio",
            context=context,
            context_token_keys=("attio_token",),
            env_token_keys=("ATTIO_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "linkedObject": {
                    "type": "string",
                    "description": "Object type slug to filter tasks by (requires linkedRecordId)",
                },
                "linkedRecordId": {
                    "type": "string",
                    "description": "Record ID to filter tasks by (requires linkedObject)",
                },
                "assignee": {
                    "type": "string",
                    "description": "Assignee email or member ID to filter by",
                },
                "isCompleted": {
                    "type": "boolean",
                    "description": "Filter by completion status",
                },
                "sort": {
                    "type": "string",
                    "description": "Sort order: created_at:asc or created_at:desc",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of tasks to return (default 500)",
                },
                "offset": {
                    "type": "number",
                    "description": "Number of tasks to skip for pagination",
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
        
        query_params: Dict[str, str] = {}
        params = parameters
        if params.get("linkedObject"):
            query_params["linked_object"] = params["linkedObject"]
        if params.get("linkedRecordId"):
            query_params["linked_record_id"] = params["linkedRecordId"]
        if params.get("assignee"):
            query_params["assignee"] = params["assignee"]
        if "isCompleted" in params:
            query_params["is_completed"] = str(bool(params["isCompleted"]))
        if params.get("sort"):
            query_params["sort"] = params["sort"]
        if "limit" in params:
            query_params["limit"] = str(params["limit"])
        if "offset" in params:
            query_params["offset"] = str(params["offset"])
        
        url = "https://api.attio.com/v2/tasks"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)
                
                if response.status_code == 200:
                    data = response.json()
                    tasks_data = data.get("data", [])
                    tasks = []
                    for task in tasks_data:
                        task_id = task.get("id", {}).get("task_id") if task.get("id") else None
                        linked_records = task.get("linked_records", [])
                        linkedRecords = [
                            {
                                "targetObjectId": r.get("target_object_id"),
                                "targetRecordId": r.get("target_record_id"),
                            }
                            for r in linked_records
                        ]
                        assignees_raw = task.get("assignees", [])
                        assignees = [
                            {
                                "type": a.get("referenced_actor_type"),
                                "id": a.get("referenced_actor_id"),
                            }
                            for a in assignees_raw
                        ]
                        created_by_actor = task.get("created_by_actor")
                        tasks.append({
                            "taskId": task_id,
                            "content": task.get("content_plaintext"),
                            "deadlineAt": task.get("deadline_at"),
                            "isCompleted": task.get("is_completed", False),
                            "linkedRecords": linkedRecords,
                            "assignees": assignees,
                            "createdByActor": created_by_actor,
                            "createdAt": task.get("created_at"),
                        })
                    result = {
                        "tasks": tasks,
                        "count": len(tasks),
                    }
                    output = json.dumps(result)
                    return ToolResult(success=True, output=output, data=result)
                else:
                    error_data = response.json()
                    error_msg = error_data.get("message", "Failed to list tasks")
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")