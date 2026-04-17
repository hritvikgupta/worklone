from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class AgentmailUpdateMessageTool(BaseTool):
    name = "agentmail_update_message"
    description = "Add or remove labels on an email message in AgentMail"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="apiKey",
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
            context_token_keys=("apiKey",),
            env_token_keys=("AGENTMAIL_API_KEY",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "inboxId": {
                    "type": "string",
                    "description": "ID of the inbox containing the message",
                },
                "messageId": {
                    "type": "string",
                    "description": "ID of the message to update",
                },
                "addLabels": {
                    "type": "string",
                    "description": "Comma-separated labels to add to the message",
                },
                "removeLabels": {
                    "type": "string",
                    "description": "Comma-separated labels to remove from the message",
                },
            },
            "required": ["inboxId", "messageId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        url = f"https://api.agentmail.to/v0/inboxes/{parameters['inboxId'].strip()}/messages/{parameters['messageId'].strip()}"

        body: dict = {}
        add_labels_str = parameters.get("addLabels")
        if add_labels_str:
            body["add_labels"] = [l.strip() for l in add_labels_str.split(",")]
        remove_labels_str = parameters.get("removeLabels")
        if remove_labels_str:
            body["remove_labels"] = [l.strip() for l in remove_labels_str.split(",")]

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")