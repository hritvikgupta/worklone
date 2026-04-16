from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class MicrosoftPlannerDeleteTaskTool(BaseTool):
    name = "microsoft_planner_delete_task"
    description = "Delete a task from Microsoft Planner"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="access_token",
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
        if '\\"' in cleaned:
            cleaned = cleaned.replace('\\"', '"')
        return cleaned

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "taskId": {
                    "type": "string",
                    "description": "The ID of the task to delete (e.g., \"pbT5K2OVkkO1M7r5bfsJ6JgAGD5m\")",
                },
                "etag": {
                    "type": "string",
                    "description": "The ETag value from the task to delete (If-Match header)",
                },
            },
            "required": ["taskId", "etag"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        task_id = parameters.get("taskId")
        etag = parameters.get("etag")

        if not task_id:
            return ToolResult(success=False, output="", error="Task ID is required")
        if not etag:
            return ToolResult(success=False, output="", error="ETag is required")

        cleaned_etag = self._clean_etag(etag)

        headers = {
            "Authorization": f"Bearer {access_token}",
            "If-Match": cleaned_etag,
        }

        url = f"https://graph.microsoft.com/v1.0/planner/tasks/{task_id}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(
                        success=True,
                        output="Task deleted successfully",
                        data={"deleted": True, "metadata": {}},
                    )
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")