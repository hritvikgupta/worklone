from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class RedditVoteTool(BaseTool):
    name = "reddit_vote"
    description = "Upvote, downvote, or unvote a Reddit post or comment"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="REDDIT_ACCESS_TOKEN",
                description="Reddit access token",
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
                "id": {
                    "type": "string",
                    "description": 'Thing fullname to vote on (e.g., "t3_abc123" for post, "t1_def456" for comment)',
                },
                "dir": {
                    "type": "number",
                    "description": "Vote direction: 1 (upvote), 0 (unvote), or -1 (downvote)",
                },
            },
            "required": ["id", "dir"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        dir_val = parameters.get("dir")
        if dir_val not in [1, 0, -1]:
            return ToolResult(success=False, output="", error="dir must be 1 (upvote), 0 (unvote), or -1 (downvote)")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "User-Agent": "sim-studio/1.0 (https://github.com/simstudioai/sim)",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        
        url = "https://oauth.reddit.com/api/vote"
        body_data = {
            "id": parameters["id"],
            "dir": str(parameters["dir"]),
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, data=body_data)
                
                try:
                    data = response.json()
                except:
                    data = None
                
                if response.status_code == 200:
                    action = "upvoted" if parameters["dir"] == 1 else "downvoted" if parameters["dir"] == -1 else "unvoted"
                    message = f"Successfully {action} {parameters['id']}"
                    result_data = {
                        "success": True,
                        "message": message,
                    }
                    return ToolResult(success=True, output=json.dumps(result_data), data=result_data)
                else:
                    result_data = {
                        "success": False,
                        "message": "Failed to vote",
                        "data": data or {"error": response.text},
                    }
                    return ToolResult(success=False, output=json.dumps(result_data), data=result_data)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")