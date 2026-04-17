from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GammaListThemesTool(BaseTool):
    name = "gamma_list_themes"
    description = "List available themes in your Gamma workspace. Returns theme IDs, names, and keywords for styling."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GAMMA_API_KEY",
                description="Gamma API key",
                env_var="GAMMA_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query to filter themes by name (case-insensitive)",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of themes to return per page (max 50)",
                },
                "after": {
                    "type": "string",
                    "description": "Pagination cursor from a previous response (nextCursor) to fetch the next page",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("GAMMA_API_KEY") if context else None
        
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="API key not configured.")
        
        headers = {
            "X-API-KEY": api_key,
        }
        
        url = "https://public-api.gamma.app/v1.0/themes"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=parameters)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")