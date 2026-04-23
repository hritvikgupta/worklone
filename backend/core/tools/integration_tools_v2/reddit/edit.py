from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class RedditEditTool(BaseTool):
    name = "reddit_edit"
    description = "Edit the text of your own Reddit post or comment"
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
                "thing_id": {
                    "type": "string",
                    "description": 'Thing fullname to edit (e.g., "t3_abc123" for post, "t1_def456" for comment)'
                },
                "text": {
                    "type": "string",
                    "description": 'New text content in markdown format (e.g., "Updated **content** here")'
                }
            },
            "required": ["thing_id", "text"]
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
        
        url = "https://oauth.reddit.com/api/editusertext"
        body = {
            "thing_id": parameters["thing_id"],
            "text": parameters["text"],
            "api_type": "json",
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, data=body)
                
                if response.status_code not in [200, 201, 204]:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                json_data = data.get("json", {})
                errors = json_data.get("errors", [])
                if errors:
                    error_msg = ", ".join(": ".join(map(str, err)) for err in errors)
                    return ToolResult(success=False, output="", error=f"Failed to edit: {error_msg}")
                
                return ToolResult(success=True, output=response.text, data=data)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")