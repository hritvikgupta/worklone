from typing import Any, Dict
import httpx
import os
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class AgentmailGetInboxTool(BaseTool):
    name = "agentmail_get_inbox"
    description = "Get details of a specific email inbox in AgentMail"
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

    def _resolve_api_key(self, context: dict | None) -> str:
        api_key = None
        if context:
            api_key = context.get("AGENTMAIL_API_KEY")
        if not api_key:
            api_key = os.getenv("AGENTMAIL_API_KEY")
        return api_key or ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "inboxId": {
                    "type": "string",
                    "description": "ID of the inbox to retrieve",
                },
            },
            "required": ["inboxId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = self._resolve_api_key(context)

        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="API key not configured.")

        headers = {
            "Authorization": f"Bearer {api_key}",
        }

        inbox_id = (parameters.get("inboxId") or "").strip()
        url = f"https://api.agentmail.to/v0/inboxes/{inbox_id}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code in [200, 201, 204]:
                    data = {}
                    try:
                        data = response.json()
                    except:
                        pass
                    transformed = {
                        "inboxId": data.get("inbox_id") or "",
                        "email": data.get("email") or "",
                        "displayName": data.get("display_name"),
                        "createdAt": data.get("created_at") or "",
                        "updatedAt": data.get("updated_at") or "",
                    }
                    return ToolResult(success=True, output=response.text, data=transformed)
                else:
                    error_msg = response.text or "Failed to get inbox"
                    try:
                        err_data = response.json()
                        error_msg = err_data.get("message") or error_msg
                    except:
                        pass
                    return ToolResult(success=False, output="", error=error_msg)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")