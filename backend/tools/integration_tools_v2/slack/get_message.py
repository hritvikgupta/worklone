from typing import Any, Dict, List
import httpx
import json
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class SlackGetMessageTool(BaseTool):
    name = "slack_get_message"
    description = "Retrieve a specific message by its timestamp. Useful for getting a thread parent message."
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
            context_token_keys=("access_token", "bot_token"),
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
                    "description": "Slack channel ID (e.g., C1234567890)",
                },
                "timestamp": {
                    "type": "string",
                    "description": "Message timestamp to retrieve (e.g., 1405894322.002768)",
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
        
        channel = (parameters.get("channel") or "").strip()
        timestamp = (parameters.get("timestamp") or "").strip()
        params_dict = {
            "channel": channel,
            "oldest": timestamp,
            "limit": "1",
            "inclusive": "true",
        }
        url = "https://slack.com/api/conversations.history"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params_dict)
                
                if response.status_code != 200:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                
                if not data.get("ok"):
                    error = data.get("error", "Unknown error")
                    if error == "missing_scope":
                        error = "Missing required permissions. Please reconnect your Slack account with the necessary scopes (channels:history, groups:history)."
                    elif error == "invalid_auth":
                        error = "Invalid authentication. Please check your Slack credentials."
                    elif error == "channel_not_found":
                        error = "Channel not found. Please check the channel ID."
                    else:
                        error = error or "Failed to get message from Slack"
                    return ToolResult(success=False, output="", error=error)
                
                messages = data.get("messages", [])
                if len(messages) == 0:
                    return ToolResult(success=False, output="", error="Message not found")
                
                msg = messages[0]
                files = [
                    {
                        "id": f.get("id"),
                        "name": f.get("name"),
                        "mimetype": f.get("mimetype"),
                        "size": f.get("size"),
                        "url_private": f.get("url_private"),
                        "permalink": f.get("permalink"),
                        "mode": f.get("mode"),
                    }
                    for f in msg.get("files", [])
                ]
                message = {
                    "type": msg.get("type", "message"),
                    "ts": msg.get("ts"),
                    "text": msg.get("text", ""),
                    "user": msg.get("user"),
                    "bot_id": msg.get("bot_id"),
                    "username": msg.get("username"),
                    "channel": msg.get("channel"),
                    "team": msg.get("team"),
                    "thread_ts": msg.get("thread_ts"),
                    "parent_user_id": msg.get("parent_user_id"),
                    "reply_count": msg.get("reply_count"),
                    "reply_users_count": msg.get("reply_users_count"),
                    "latest_reply": msg.get("latest_reply"),
                    "subscribed": msg.get("subscribed"),
                    "last_read": msg.get("last_read"),
                    "unread_count": msg.get("unread_count"),
                    "subtype": msg.get("subtype"),
                    "reactions": msg.get("reactions", []),
                    "is_starred": msg.get("is_starred", False),
                    "pinned_to": msg.get("pinned_to", []),
                    "files": files,
                    "attachments": msg.get("attachments", []),
                    "blocks": msg.get("blocks", []),
                    "edited": msg.get("edited"),
                    "permalink": msg.get("permalink"),
                }
                result_data = {"message": message}
                return ToolResult(success=True, output=json.dumps(result_data), data=result_data)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")