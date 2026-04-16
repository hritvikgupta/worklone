from typing import Any, Dict
import httpx
import json
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class SlackListChannelsTool(BaseTool):
    name = "slack_list_channels"
    description = "List all channels in a Slack workspace. Returns public and private channels the bot has access to."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="SLACK_ACCESS_TOKEN",
                description="OAuth access token or bot token for Slack API",
                env_var="SLACK_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "slack",
            context=context,
            context_token_keys=("provider_token",),
            env_token_keys=("SLACK_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "includePrivate": {
                    "type": "boolean",
                    "description": "Include private channels the bot is a member of (default: true)",
                },
                "excludeArchived": {
                    "type": "boolean",
                    "description": "Exclude archived channels (default: true)",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of channels to return (default: 100, max: 200)",
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

        include_private = parameters.get("includePrivate", True)
        types = "public_channel,private_channel" if include_private else "public_channel"

        exclude_archived = parameters.get("excludeArchived", True)
        exclude_archived_str = "true" if exclude_archived else "false"

        limit_val = parameters.get("limit", 100)
        limit_val = min(int(limit_val), 200)

        params_dict = {
            "types": types,
            "exclude_archived": exclude_archived_str,
            "limit": str(limit_val),
        }

        url = "https://slack.com/api/conversations.list"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params_dict)

                if response.status_code != 200:
                    return ToolResult(success=False, output="", error=response.text)

                data = response.json()

                if not data.get("ok", False):
                    error = data.get("error", "Failed to list channels from Slack")
                    if error == "missing_scope":
                        error = "Missing required permissions. Please reconnect your Slack account with the necessary scopes (channels:read, groups:read)."
                    elif error == "invalid_auth":
                        error = "Invalid authentication. Please check your Slack credentials."
                    return ToolResult(success=False, output="", error=error)

                channels_raw = data.get("channels", [])
                channels = []
                for channel in channels_raw:
                    topic = channel.get("topic", {})
                    purpose = channel.get("purpose", {})
                    ch = {
                        "id": channel.get("id"),
                        "name": channel.get("name"),
                        "is_private": channel.get("is_private", False),
                        "is_archived": channel.get("is_archived", False),
                        "is_member": channel.get("is_member", False),
                        "num_members": channel.get("num_members"),
                        "topic": topic.get("value", ""),
                        "purpose": purpose.get("value", ""),
                        "created": channel.get("created"),
                        "creator": channel.get("creator"),
                    }
                    channels.append(ch)

                ids = [ch["id"] for ch in channels]
                names = [ch["name"] for ch in channels]

                output_data = {
                    "channels": channels,
                    "ids": ids,
                    "names": names,
                    "count": len(channels),
                }

                output_str = json.dumps(output_data, ensure_ascii=False, indent=2)
                return ToolResult(success=True, output=output_str, data=output_data)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")