from typing import Any, Dict
import httpx
import os
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class ZepGetMessagesTool(BaseTool):
    name = "zep_get_messages"
    description = "Retrieve messages from a thread"
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

    def _resolve_access_token(self, context: dict | None) -> str:
        token = (context or {}).get("ZEP_API_KEY")
        if not token:
            token = os.getenv("ZEP_API_KEY")
        return token or ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "threadId": {
                    "type": "string",
                    "description": 'Thread ID to get messages from (e.g., "thread_abc123")',
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of messages to return (e.g., 10, 50, 100)",
                },
                "cursor": {
                    "type": "string",
                    "description": "Cursor for pagination",
                },
                "lastn": {
                    "type": "number",
                    "description": "Number of most recent messages to return (overrides limit and cursor)",
                },
            },
            "required": ["threadId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Zep API key not configured.")
        
        headers = {
            "Authorization": f"Api-Key {access_token}",
            "Content-Type": "application/json",
        }
        
        params: dict[str, Any] = {}
        limit = parameters.get("limit")
        if limit is not None:
            params["limit"] = int(limit)
        cursor = parameters.get("cursor")
        if cursor:
            params["cursor"] = cursor
        lastn = parameters.get("lastn")
        if lastn is not None:
            params["lastn"] = int(lastn)
        
        url = f"https://api.getzep.com/api/v2/threads/{parameters['threadId']}/messages"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")