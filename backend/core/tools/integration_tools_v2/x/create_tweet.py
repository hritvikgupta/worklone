from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class XCreateTweetTool(BaseTool):
    name = "x_create_tweet"
    description = "Create a new tweet, reply, or quote tweet on X"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="X_ACCESS_TOKEN",
                description="X OAuth access token",
                env_var="X_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "x",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("X_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text content of the tweet (max 280 characters)",
                },
                "replyToTweetId": {
                    "type": "string",
                    "description": "Tweet ID to reply to",
                },
                "quoteTweetId": {
                    "type": "string",
                    "description": "Tweet ID to quote",
                },
                "mediaIds": {
                    "type": "string",
                    "description": "Comma-separated media IDs to attach (up to 4)",
                },
                "replySettings": {
                    "type": "string",
                    "description": 'Who can reply: "mentionedUsers", "following", "subscribers", or "verified"',
                },
            },
            "required": ["text"],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = "https://api.x.com/2/tweets"
        
        body: Dict[str, Any] = {"text": parameters["text"]}
        
        reply_to_tweet_id = parameters.get("replyToTweetId")
        if reply_to_tweet_id:
            body["reply"] = {"in_reply_to_tweet_id": reply_to_tweet_id.strip()}
        
        quote_tweet_id = parameters.get("quoteTweetId")
        if quote_tweet_id:
            body["quote_tweet_id"] = quote_tweet_id.strip()
        
        media_ids_str = parameters.get("mediaIds")
        if media_ids_str:
            ids = [id.strip() for id in media_ids_str.split(",") if id.strip()]
            if ids:
                body["media"] = {"media_ids": ids}
        
        reply_settings = parameters.get("replySettings")
        if reply_settings:
            body["reply_settings"] = reply_settings
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")