from typing import Any, Dict
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class CursorListAgentsTool(BaseTool):
    name = "cursor_list_agents"
    description = "List all cloud agents for the authenticated user with optional pagination. Returns API-aligned fields only."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="cursor_api_key",
                description="Cursor API key",
                env_var="CURSOR_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def _resolve_api_key(self, context: dict | None) -> str:
        if context is None:
            return ""
        api_key = context.get("cursor_api_key")
        if self._is_placeholder_token(api_key or ""):
            return ""
        return api_key or ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "number",
                    "description": "Number of agents to return (default: 20, max: 100)",
                },
                "cursor": {
                    "type": "string",
                    "description": "Pagination cursor from previous response",
                },
                "prUrl": {
                    "type": "string",
                    "description": "Filter agents by pull request URL",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = self._resolve_api_key(context)
        
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Cursor API key not configured.")
        
        headers = {
            "Authorization": f"Basic {base64.b64encode(f'{api_key}:'.encode('utf-8')).decode('utf-8')}",
        }
        
        url = "https://api.cursor.com/v0/agents"
        query_params = {}
        if "limit" in parameters:
            query_params["limit"] = parameters["limit"]
        if "cursor" in parameters:
            query_params["cursor"] = parameters["cursor"]
        if "prUrl" in parameters:
            query_params["prUrl"] = parameters["prUrl"]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=query_params, headers=headers)
                
                if response.status_code in [200]:
                    data = response.json()
                    return ToolResult(
                        success=True,
                        output=f"Found {len(data.get('agents', []))} agents",
                        data=data,
                    )
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")