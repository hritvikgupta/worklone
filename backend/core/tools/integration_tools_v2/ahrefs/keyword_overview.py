from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class AhrefsKeywordOverviewTool(BaseTool):
    name = "ahrefs_keyword_overview"
    description = "Get detailed metrics for a keyword including search volume, keyword difficulty, CPC, clicks, and traffic potential."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="AHREFS_API_KEY",
                description="Ahrefs API Key",
                env_var="AHREFS_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "The keyword to analyze",
                },
                "country": {
                    "type": "string",
                    "description": 'Country code for keyword data. Example: "us", "gb", "de" (default: "us")',
                },
            },
            "required": ["keyword"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("AHREFS_API_KEY") if context else None

        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Ahrefs API key not configured.")

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        keyword = parameters["keyword"]
        country = parameters.get("country", "us")
        query_params = {
            "keyword": keyword,
            "country": country,
        }
        url = "https://api.ahrefs.com/v3/keywords-explorer/overview"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")