from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class SalesforceDeleteTaskTool(BaseTool):
    name = "salesforce_delete_task"
    description = "Delete a task"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="SALESFORCE_ACCESS_TOKEN",
                description="Salesforce access token",
                env_var="SALESFORCE_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_credentials(self, context: dict | None) -> Dict[str, str]:
        connection = await resolve_oauth_connection(
            "salesforce",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("SALESFORCE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        access_token = connection.access_token
        instance_url = getattr(connection, "instance_url", None)
        return {"access_token": access_token, "instance_url": instance_url}

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "taskId": {
                    "type": "string",
                    "description": "Salesforce Task ID to delete (18-character string starting with 00T)",
                },
            },
            "required": ["taskId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        credentials = await self._resolve_credentials(context)
        access_token = credentials["access_token"]
        instance_url = credentials["instance_url"]

        if self._is_placeholder_token(access_token) or not instance_url:
            return ToolResult(success=False, output="", error="Salesforce access token or instance URL not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
        }

        task_id = parameters["taskId"]
        url = f"{instance_url.rstrip('/')}/services/data/v59.0/sobjects/Task/{task_id}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(
                        success=True,
                        output="",
                        data={
                            "success": True,
                            "output": {
                                "id": task_id,
                                "deleted": True,
                            },
                        },
                    )
                else:
                    try:
                        error_data = response.json()
                    except Exception:
                        error_data = {}
                    if isinstance(error_data, list) and error_data:
                        error_msg = error_data[0].get("message", str(error_data[0]))
                    elif isinstance(error_data, dict):
                        error_msg = error_data.get("message", str(error_data))
                    else:
                        error_msg = response.text or "Failed to delete task"
                    return ToolResult(success=False, output="", error=error_msg)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")