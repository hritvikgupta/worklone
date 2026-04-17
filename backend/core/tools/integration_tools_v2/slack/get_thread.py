from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class SlackGetThreadTool(BaseTool):
    name = "slack_get_thread"
    description = "Retrieve an entire thread including the parent message and all replies. Useful for getting full conversation context."
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

    def _transform_message(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "type": msg.get("type", "message"),
            "ts": msg["ts"],
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
            "files": [
                {
                    "id": f["id"],
                    "name": f["name"],
                    "mimetype": f.get("mimetype"),
                    "size": f["size"],
                    "url_private": f.get("url_private"),
                    "permalink": f.get("permalink"),
                    "mode": f.get("mode"),
                }
                for f in msg.get("files", [])
            ],
            "attachments": msg.get("attachments", []),
            "blocks": msg.get("blocks", []),
            "edited": msg.get("edited"),
            "permalink": msg.get("permalink"),
        }

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "channel": {
                    "type": "string",
                    "description": "Slack channel ID (e.g., C1234567890)",
                },
                "threadTs": {
                    "type": "string",
                    "description": "Thread timestamp (thread_ts) to retrieve (e.g., 1405894322.002768)",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of messages to return (default: 100, max: 200)",
                },
            },
            "required": ["channel", "threadTs"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = "https://slack.com/api/conversations.replies"
        channel = (parameters.get("channel") or "").strip()
        thread_ts = (parameters.get("threadTs") or "").strip()
        limit_val = parameters.get("limit")
        limit = min(int(limit_val) if limit_val is not None else 100, 200)
        params = {
            "channel": channel,
            "ts": thread_ts,
            "inclusive": "true",
            "limit": str(limit),
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params)
                
                if response.status_code != 200:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                
                if not data.get("ok", False):
                    error = data.get("error")
                    error_msgs = {
                        "missing_scope": "Missing required permissions. Please reconnect your Slack account with the necessary scopes (channels:history, groups:history).",
                        "invalid_auth": "Invalid authentication. Please check your Slack credentials.",
                        "channel_not_found": "Channel not found. Please check the channel ID.",
                        "thread_not_found": "Thread not found. Please check the thread timestamp.",
                    }
                    error_msg = error_msgs.get(error, error or "Failed to get thread from Slack")
                    return ToolResult(success=False, output="", error=error_msg)
                
                raw_messages = data.get("messages", [])
                if len(raw_messages) == 0:
                    return ToolResult(success=False, output="", error="Thread not found")
                
                messages = [self._transform_message(msg) for msg in raw_messages]
                parent_message = messages[0]
                replies = messages[1:]
                transformed = {
                    "parentMessage": parent_message,
                    "replies": replies,
                    "messages": messages,
                    "replyCount": len(replies),
                    "hasMore": data.get("has_more", False),
                }
                output = json.dumps(transformed, indent=2)
                return ToolResult(success=True, output=output, data=transformed)
                    
        except httpx.HTTPStatusError as e:
            return ToolResult(success=False, output="", error=f"HTTP error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")