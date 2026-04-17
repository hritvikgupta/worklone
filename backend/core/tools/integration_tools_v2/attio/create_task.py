from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class AttioCreateTaskTool(BaseTool):
    name = "attio_create_task"
    description = "Create a task in Attio"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

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
            context_token_keys=("accessToken",),
            env_token_keys=("ATTIO_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The task content (max 2000 characters)",
                },
                "deadlineAt": {
                    "type": "string",
                    "description": "Deadline in ISO 8601 format (e.g. 2024-12-01T15:00:00.000Z)",
                },
                "isCompleted": {
                    "type": "boolean",
                    "description": "Whether the task is completed (default false)",
                },
                "linkedRecords": {
                    "type": "string",
                    "description": 'JSON array of linked records (e.g. [{"target_object":"people","target_record_id":"..."}])',
                },
                "assignees": {
                    "type": "string",
                    "description": 'JSON array of assignees (e.g. [{"referenced_actor_type":"workspace-member","referenced_actor_id":"..."}])',
                },
            },
            "required": ["content"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = "https://api.attio.com/v2/tasks"
        
        linked_records: list[Any] = []
        lr = parameters.get("linkedRecords")
        if lr:
            try:
                if isinstance(lr, str):
                    linked_records = json.loads(lr)
                else:
                    linked_records = lr
            except json.JSONDecodeError:
                linked_records = []
        
        assignees: list[Any] = []
        a = parameters.get("assignees")
        if a:
            try:
                if isinstance(a, str):
                    assignees = json.loads(a)
                else:
                    assignees = a
            except json.JSONDecodeError:
                assignees = []
        
        json_body = {
            "data": {
                "content": parameters["content"],
                "format": "plaintext",
                "deadline_at": parameters.get("deadlineAt"),
                "is_completed": parameters.get("isCompleted", False),
                "linked_records": linked_records,
                "assignees": assignees,
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=json_body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")