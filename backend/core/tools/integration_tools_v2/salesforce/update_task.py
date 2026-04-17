from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection

class SalesforceUpdateTaskTool(BaseTool):
    name = "salesforce_update_task"
    description = "Update an existing task"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="accessToken",
                description="Salesforce access token",
                env_var="SALESFORCE_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_connection(self, context: dict | None) -> Any:
        connection = await resolve_oauth_connection(
            "salesforce",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("SALESFORCE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "taskId": {
                    "type": "string",
                    "description": "Salesforce Task ID to update (18-character string starting with 00T)",
                },
                "subject": {
                    "type": "string",
                    "description": "Task subject",
                },
                "status": {
                    "type": "string",
                    "description": "Status (e.g., Not Started, In Progress, Completed)",
                },
                "priority": {
                    "type": "string",
                    "description": "Priority (e.g., Low, Normal, High)",
                },
                "activityDate": {
                    "type": "string",
                    "description": "Due date in YYYY-MM-DD format",
                },
                "description": {
                    "type": "string",
                    "description": "Task description",
                },
            },
            "required": ["taskId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        connection = await self._resolve_connection(context)
        access_token = connection.access_token
        instance_url = connection.instance_url

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        task_id = parameters["taskId"]
        url = f"{instance_url.rstrip('/')}/services/data/v59.0/sobjects/Task/{task_id}"

        body: Dict[str, Any] = {}
        for field, param_key in [
            ("Subject", "subject"),
            ("Status", "status"),
            ("Priority", "priority"),
            ("ActivityDate", "activityDate"),
            ("Description", "description"),
        ]:
            if param_key in parameters:
                value = parameters[param_key]
                if value:
                    body[field] = value

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    data = response.json() if response.content else {}
                    return ToolResult(success=True, output=response.text, data=data)
                else:
                    try:
                        error_data = response.json()
                        if isinstance(error_data, list) and error_data and isinstance(error_data[0], dict) and "message" in error_data[0]:
                            error_msg = error_data[0]["message"]
                        else:
                            error_msg = error_data.get("message", str(error_data))
                    except Exception:
                        error_msg = response.text
                    return ToolResult(success=False, output="", error=error_msg)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")