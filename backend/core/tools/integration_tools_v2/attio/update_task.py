from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class AttioUpdateTaskTool(BaseTool):
    name = "attio_update_task"
    description = "Update a task in Attio (deadline, completion status, linked records, assignees)"
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
            context_token_keys=("provider_token",),
            env_token_keys=("ATTIO_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "taskId": {
                    "type": "string",
                    "description": "The ID of the task to update",
                },
                "deadlineAt": {
                    "type": "string",
                    "description": "New deadline in ISO 8601 format",
                },
                "isCompleted": {
                    "type": "boolean",
                    "description": "Whether the task is completed",
                },
                "linkedRecords": {
                    "type": "string",
                    "description": "JSON array of linked records",
                },
                "assignees": {
                    "type": "string",
                    "description": "JSON array of assignees",
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

        task_id = parameters["taskId"].strip()
        url = f"https://api.attio.com/v2/tasks/{task_id}"

        data: Dict[str, Any] = {}
        deadline_at = parameters.get("deadlineAt")
        if deadline_at is not None:
            data["deadline_at"] = deadline_at or None
        is_completed = parameters.get("isCompleted")
        if is_completed is not None:
            data["is_completed"] = is_completed
        linked_records_val = parameters.get("linkedRecords")
        if linked_records_val:
            try:
                if isinstance(linked_records_val, str):
                    data["linked_records"] = json.loads(linked_records_val)
                else:
                    data["linked_records"] = linked_records_val
            except:
                data["linked_records"] = []
        assignees_val = parameters.get("assignees")
        if assignees_val:
            try:
                if isinstance(assignees_val, str):
                    data["assignees"] = json.loads(assignees_val)
                else:
                    data["assignees"] = assignees_val
            except:
                data["assignees"] = []

        json_body = {"data": data}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(url, headers=headers, json=json_body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")