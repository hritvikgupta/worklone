from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class RedditSendMessageTool(BaseTool):
    name = "reddit_send_message"
    description = "Send a private message to a Reddit user"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

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
            context_token_keys=("provider_token",),
            env_token_keys=("REDDIT_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "to": {
                    "type": "string",
                    "description": 'Recipient username (e.g., "example_user") or subreddit (e.g., "/r/subreddit")',
                },
                "subject": {
                    "type": "string",
                    "description": "Message subject (max 100 characters)",
                },
                "text": {
                    "type": "string",
                    "description": "Message body in markdown format",
                },
                "from_sr": {
                    "type": "string",
                    "description": "Subreddit name to send the message from (requires moderator mail permission)",
                },
            },
            "required": ["to", "subject", "text"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "User-Agent": "sim-studio/1.0 (https://github.com/simstudioai/sim)",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        
        url = "https://oauth.reddit.com/api/compose"
        
        body = {
            "to": parameters["to"].strip(),
            "subject": parameters["subject"],
            "text": parameters["text"],
            "api_type": "json",
        }
        if parameters.get("from_sr"):
            body["from_sr"] = parameters["from_sr"].strip()
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, data=body)
                
                resp_data = response.json()
                
                if response.status_code >= 400:
                    error_msg = resp_data.get("message", f"HTTP error {response.status_code}")
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Failed to send message: {error_msg}",
                    )
                
                json_data = resp_data.get("json", {})
                if json_data.get("errors") and len(json_data["errors"]) > 0:
                    errors = ", ".join(": ".join(map(str, err)) for err in json_data["errors"])
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Failed to send message: {errors}",
                    )
                
                return ToolResult(success=True, output=response.text, data=resp_data)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")