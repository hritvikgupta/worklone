from typing import Any, Dict
import httpx
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class SlackDeleteMessageTool(BaseTool):
    name = "slack_delete_message"
    description = "Delete a message previously sent by the bot in Slack"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="SLACK_ACCESS_TOKEN",
                description="Slack access token or bot token",
                env_var="SLACK_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "slack",
            context=context,
            context_token_keys=("accessToken", "botToken"),
            env_token_keys=("SLACK_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "channel": {
                    "type": "string",
                    "description": "Channel ID where the message was posted (e.g., C1234567890)",
                },
                "timestamp": {
                    "type": "string",
                    "description": "Timestamp of the message to delete (e.g., 1405894322.002768)",
                },
            },
            "required": ["channel", "timestamp"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        url = "https://slack.com/api/chat.delete"

        body = {
            "channel": parameters["channel"],
            "ts": parameters["timestamp"],
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code != 200:
                    return ToolResult(success=False, output="", error=response.text)

                data = response.json()

                if data.get("ok"):
                    output_data = {
                        "content": "Message deleted successfully",
                        "metadata": {
                            "channel": data.get("channel", ""),
                            "timestamp": data.get("ts", ""),
                        },
                    }
                    return ToolResult(success=True, output=str(output_data), data=output_data)
                else:
                    error_msg = data.get("error", "Failed to delete message")
                    return ToolResult(success=False, output="", error=error_msg)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")