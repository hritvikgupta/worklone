from typing import Any, Dict
import httpx
import urllib.parse
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class MicrosoftTeamsUpdateChatMessageTool(BaseTool):
    name = "update_microsoft_teams_chat_message"
    description = "Update an existing message in a Microsoft Teams chat"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="MICROSOFT_TEAMS_ACCESS_TOKEN",
                description="Access token",
                env_var="MICROSOFT_TEAMS_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "microsoft-teams",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("MICROSOFT_TEAMS_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "chatId": {
                    "type": "string",
                    "description": "The ID of the chat containing the message (e.g., \"19:abc123def456@thread.v2\")",
                },
                "messageId": {
                    "type": "string",
                    "description": "The ID of the message to update (numeric string from message responses)",
                },
                "content": {
                    "type": "string",
                    "description": "The new content for the message (plain text or HTML formatted)",
                },
            },
            "required": ["chatId", "messageId", "content"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        chat_id = parameters.get("chatId", "").strip()
        message_id = parameters.get("messageId", "").strip()
        content = parameters.get("content", "")

        if not chat_id:
            return ToolResult(success=False, output="", error="Chat ID is required.")
        if not message_id:
            return ToolResult(success=False, output="", error="Message ID is required.")
        if not content:
            return ToolResult(success=False, output="", error="Content is required.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        url = (
            f"https://graph.microsoft.com/v1.0/chats/"
            f"{urllib.parse.quote(chat_id)}/messages/{urllib.parse.quote(message_id)}"
        )

        body = {
            "body": {
                "contentType": "text",
                "content": content,
            }
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    data: Dict[str, Any] = {}
                    if response.status_code != 204 and response.text:
                        data = response.json()

                    metadata = {
                        "messageId": data.get("id") or message_id,
                        "chatId": data.get("chatId") or chat_id,
                        "content": data.get("body", {}).get("content") or content,
                        "createdTime": data.get("createdDateTime", ""),
                        "url": data.get("webUrl", ""),
                    }
                    result = {"updatedContent": True, "metadata": metadata}
                    return ToolResult(success=True, output=str(result), data=result)
                else:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("error", {}).get("message", response.text)
                    except Exception:
                        error_msg = response.text
                    return ToolResult(success=False, output="", error=error_msg)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
