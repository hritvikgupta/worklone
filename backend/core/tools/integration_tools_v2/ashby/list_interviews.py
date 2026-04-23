from typing import Any, Dict
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class AshbyListInterviewsTool(BaseTool):
    name = "ashby_list_interviews"
    description = "Lists interview schedules in Ashby, optionally filtered by application or interview stage."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="ASHBY_API_KEY",
                description="Ashby API Key",
                env_var="ASHBY_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "ashby",
            context=context,
            context_token_keys=("ashby_api_key",),
            env_token_keys=("ASHBY_API_KEY",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "applicationId": {
                    "type": "string",
                    "description": "The UUID of the application to list interview schedules for",
                },
                "interviewStageId": {
                    "type": "string",
                    "description": "The UUID of the interview stage to list interview schedules for",
                },
                "cursor": {
                    "type": "string",
                    "description": "Opaque pagination cursor from a previous response nextCursor value",
                },
                "perPage": {
                    "type": "number",
                    "description": "Number of results per page (default 100)",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Basic {base64.b64encode(f'{access_token}:'.encode('utf-8')).decode('utf-8')}",
            "Content-Type": "application/json",
        }

        url = "https://api.ashbyhq.com/interviewSchedule.list"

        body = {}
        for param in ["applicationId", "interviewStageId", "cursor"]:
            value = parameters.get(param)
            if value is not None:
                body[param] = value
        per_page = parameters.get("perPage")
        if per_page is not None:
            body["limit"] = per_page

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code not in [200, 201, 204]:
                    return ToolResult(success=False, output="", error=response.text)

                data = response.json()
                if not isinstance(data, dict) or not data.get("success", False):
                    error_msg = (
                        data.get("errorInfo", {}).get("message", "Failed to list interview schedules")
                        if isinstance(data, dict)
                        else "Invalid response"
                    )
                    return ToolResult(success=False, output="", error=error_msg)

                return ToolResult(success=True, output=response.text, data=data)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")