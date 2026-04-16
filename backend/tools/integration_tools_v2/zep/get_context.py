from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection

class ZepGetContextTool(BaseTool):
    name = "Get User Context"
    description = "Retrieve user context from a thread with summary or basic mode"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="ZEP_API_KEY",
                description="Your Zep API key",
                env_var="ZEP_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "zep",
            context=context,
            context_token_keys=("zep_api_key",),
            env_token_keys=("ZEP_API_KEY",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "threadId": {
                    "type": "string",
                    "description": 'Thread ID to get context from (e.g., "thread_abc123")',
                },
                "mode": {
                    "type": "string",
                    "description": 'Context mode: "summary" (natural language) or "basic" (raw facts)',
                    "default": "summary",
                },
                "minRating": {
                    "type": "number",
                    "description": "Minimum rating by which to filter relevant facts",
                },
            },
            "required": ["threadId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Api-Key {access_token}",
            "Content-Type": "application/json",
        }
        
        url = f"https://api.getzep.com/api/v2/threads/{parameters['threadId']}/context"
        
        params_dict = {
            "mode": parameters.get("mode", "summary"),
        }
        min_rating = parameters.get("minRating")
        if min_rating is not None:
            params_dict["minRating"] = min_rating
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params_dict)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")