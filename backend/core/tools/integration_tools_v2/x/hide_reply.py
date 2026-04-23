from typing import Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection

class XHideReplyTool(BaseTool):
    name = "X Hide Reply"
    description = "Hide or unhide a reply to a tweet authored by the authenticated user"
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
                "tweetId": {
                    "type": "string",
                    "description": "The reply tweet ID to hide or unhide",
                },
                "hidden": {
                    "type": "boolean",
                    "description": "Set to true to hide the reply, false to unhide",
                },
            },
            "required": ["tweetId", "hidden"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        tweet_id = str(parameters["tweetId"]).strip()
        hidden = parameters["hidden"]
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = f"https://api.x.com/2/tweets/{tweet_id}/hidden"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.put(url, headers=headers, json={"hidden": hidden})
                
            if response.status_code not in [200]:
                return ToolResult(success=False, output="", error=response.text)
                
            try:
                data = response.json()
            except Exception:
                return ToolResult(success=True, output=response.text, data={})
                
            if not data.get("data"):
                errors = data.get("errors", [])
                error_msg = errors[0].get("detail") if errors else "Failed to hide/unhide reply"
                return ToolResult(success=False, output="", error=error_msg)
            
            hidden_result = data["data"].get("hidden", False)
            return ToolResult(
                success=True,
                output=response.text,
                data={"hidden": hidden_result},
            )
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")