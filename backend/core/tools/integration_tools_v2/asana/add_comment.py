from typing import Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class AsanaAddCommentTool(BaseTool):
    name = "asana_add_comment"
    description = "Add a comment (story) to an Asana task"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="ASANA_ACCESS_TOKEN",
                description="OAuth access token for Asana",
                env_var="ASANA_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "asana",
            context=context,
            context_token_keys=("asana_token",),
            env_token_keys=("ASANA_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "taskGid": {
                    "type": "string",
                    "description": "Asana task GID (numeric string)",
                },
                "text": {
                    "type": "string",
                    "description": "The text content of the comment",
                },
            },
            "required": ["taskGid", "text"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        task_gid = parameters["taskGid"]
        text = parameters["text"]

        url = f"https://app.asana.com/api/1.0/tasks/{task_gid}/stories"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        body = {
            "data": {
                "text": text,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    error_text = response.text
                    error_message = f"Asana API error: {response.status_code} {response.reason_phrase}"
                    try:
                        error_data = response.json()
                        asana_errors = error_data.get("errors", [])
                        if asana_errors:
                            asana_error = asana_errors[0]
                            error_message = asana_error.get("message", error_message)
                            if asana_error.get("help"):
                                error_message += f" ({asana_error['help']})"
                    except Exception:
                        pass
                    return ToolResult(success=False, output="", error=error_message)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")