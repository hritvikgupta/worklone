from typing import Dict, Any
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection

class AgentmailCreateInboxTool(BaseTool):
    name = "Create Inbox"
    description = "Create a new email inbox with AgentMail"
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
        connection = await resolve_oauth_connection(
            "agentmail",
            context=context,
            context_token_keys=("AGENTMAIL_API_KEY",),
            env_token_keys=("AGENTMAIL_API_KEY",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "username": {
                    "type": "string",
                    "description": "Username for the inbox email address",
                },
                "domain": {
                    "type": "string",
                    "description": "Domain for the inbox email address",
                },
                "displayName": {
                    "type": "string",
                    "description": "Display name for the inbox",
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
            "Content-Type": "application/json",
        }

        url = "https://api.agentmail.to/v0/inboxes"

        body: dict = {}
        username = parameters.get("username")
        if username:
            body["username"] = username
        domain = parameters.get("domain")
        if domain:
            body["domain"] = domain
        display_name = parameters.get("displayName")
        if display_name:
            body["display_name"] = display_name

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")