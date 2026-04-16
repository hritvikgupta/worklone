from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class SlackAddReactionTool(BaseTool):
    name = "slack_add_reaction"
    description = "Add an emoji reaction to a Slack message"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="SLACK_ACCESS_TOKEN",
                description="Access token or bot token for Slack API",
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
                    "description": "Timestamp of the message to react to (e.g., 1405894322.002768)",
                },
                "name": {
                    "type": "string",
                    "description": "Name of the emoji reaction (without colons, e.g., thumbsup, heart, eyes)",
                },
            },
            "required": ["channel", "timestamp", "name"],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        url = "https://slack.com/api/reactions.add"

        json_body = {
            "channel": parameters["channel"],
            "timestamp": parameters["timestamp"],
            "name": parameters["name"],
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=json_body)
                data = response.json()

                if response.status_code == 200 and data.get("ok"):
                    content = f"Successfully added :{parameters['name']}: reaction"
                    metadata = {
                        "channel": parameters["channel"],
                        "timestamp": parameters["timestamp"],
                        "reaction": parameters["name"],
                    }
                    output_data = {"content": content, "metadata": metadata}
                    return ToolResult(
                        success=True, output=content, data=output_data
                    )
                else:
                    error_msg = data.get("error", "Failed to add reaction")
                    return ToolResult(
                        success=False, output="", error=error_msg
                    )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")