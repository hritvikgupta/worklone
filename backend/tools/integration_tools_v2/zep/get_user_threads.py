from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ZepGetUserThreadsTool(BaseTool):
    name = "Get User Threads"
    description = "List all conversation threads for a specific user"
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
                "userId": {
                    "type": "string",
                    "description": 'User ID to get threads for (e.g., "user_123")',
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of threads to return (e.g., 10, 25, 50)",
                    "default": 10,
                },
            },
            "required": ["userId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Zep API key not configured.")
        
        headers = {
            "Authorization": f"Api-Key {access_token}",
            "Content-Type": "application/json",
        }
        
        user_id = parameters["userId"]
        limit = int(parameters.get("limit", 10))
        url = f"https://api.getzep.com/api/v2/users/{user_id}/threads?limit={limit}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")