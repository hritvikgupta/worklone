from typing import Any, Dict
import httpx
import os
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class AgentmailGetThreadTool(BaseTool):
    name = "agentmail_get_thread"
    description = "Get details of a specific email thread including messages in AgentMail"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="AGENTMAIL_API_KEY",
                description="AgentMail API key",
                env_var="AGENTMAIL_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        access_token = None
        if context is not None:
            access_token = context.get("AGENTMAIL_API_KEY")
        if access_token is None:
            access_token = os.environ.get("AGENTMAIL_API_KEY")
        if self._is_placeholder_token(access_token or ""):
            return ""
        return access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "inboxId": {
                    "type": "string",
                    "description": "ID of the inbox containing the thread",
                },
                "threadId": {
                    "type": "string",
                    "description": "ID of the thread to retrieve",
                },
            },
            "required": ["inboxId", "threadId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
        }

        inbox_id = parameters["inboxId"].strip()
        thread_id = parameters["threadId"].strip()
        url = f"https://api.agentmail.to/v0/inboxes/{inbox_id}/threads/{thread_id}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")