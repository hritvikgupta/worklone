from typing import Any, Dict
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class XWriteTool(BaseTool):
    name = "x_write"
    description = "Post new tweets, reply to tweets, or create polls on X (Twitter)"
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
            context_token_keys=("access_token",),
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
                    "description": "The text content of your tweet (max 280 characters)"
                },
                "replyTo": {
                    "type": "string",
                    "description": "ID of the tweet to reply to (e.g., 1234567890123456789)"
                },
                "mediaIds": {
                    "type": "array",
                    "description": "Array of media IDs to attach to the tweet"
                },
                "poll": {
                    "type": "object",
                    "description": "Poll configuration for the tweet"
                }
            },
            "required": ["text"]
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = "https://api.twitter.com/2/tweets"
        
        body = {
            "text": parameters["text"],
        }
        
        reply_to = parameters.get("replyTo")
        if reply_to:
            body["reply"] = {"in_reply_to_tweet_id": reply_to}
        
        media_ids = parameters.get("mediaIds")
        if media_ids:
            body["media"] = {"media_ids": media_ids}
        
        poll_param = parameters.get("poll")
        if poll_param:
            body["poll"] = {
                "options": poll_param.get("options"),
                "duration_minutes": poll_param.get("durationMinutes"),
            }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")