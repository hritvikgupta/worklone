from typing import Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class RedditSubscribeTool(BaseTool):
    name = "reddit_subscribe"
    description = "Subscribe or unsubscribe from a subreddit"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def _normalize_subreddit(self, subreddit: str) -> str:
        subreddit = subreddit.lstrip("r/").strip().lower()
        return subreddit

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="REDDIT_ACCESS_TOKEN",
                description="Access token for Reddit API",
                env_var="REDDIT_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "reddit",
            context=context,
            context_token_keys=("reddit_token",),
            env_token_keys=("REDDIT_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "subreddit": {
                    "type": "string",
                    "description": 'The subreddit to subscribe to or unsubscribe from (e.g., "technology", "programming")',
                },
                "action": {
                    "type": "string",
                    "description": 'Action to perform: "sub" to subscribe or "unsub" to unsubscribe',
                    "enum": ["sub", "unsub"],
                },
            },
            "required": ["subreddit", "action"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        subreddit = parameters.get("subreddit", "")
        action = parameters.get("action", "")

        if action not in ["sub", "unsub"]:
            return ToolResult(
                success=False,
                output="",
                error="action must be 'sub' or 'unsub'",
            )

        sr_name = self._normalize_subreddit(subreddit)

        data = {
            "action": action,
            "sr_name": sr_name,
        }

        headers = {
            "Authorization": f"Bearer {access_token}",
            "User-Agent": "sim-studio/1.0 (https://github.com/simstudioai/sim)",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        url = "https://oauth.reddit.com/api/subscribe"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, data=data)

                if response.status_code == 200:
                    action_text = "subscribed to" if action == "sub" else "unsubscribed from"
                    message = f"Successfully {action_text} r/{subreddit}"
                    result_data = {
                        "success": True,
                        "message": message,
                    }
                    return ToolResult(success=True, output=message, data=result_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")