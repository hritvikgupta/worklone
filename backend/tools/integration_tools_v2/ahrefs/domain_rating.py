from typing import Any, Dict
import httpx
import os
import datetime
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class AhrefsDomainRatingTool(BaseTool):
    name = "ahrefs_domain_rating"
    description = """Get the Domain Rating (DR) and Ahrefs Rank for a target domain. Domain Rating shows the strength of a website's backlink profile on a scale from 0 to 100."""
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

    async def _resolve_access_token(self, context: dict | None) -> str:
        api_key = context.get("AHREFS_API_KEY") if context else None
        if api_key is None:
            api_key = os.environ.get("AHREFS_API_KEY")
        return api_key or ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "The target domain to analyze (e.g., example.com)",
                },
                "date": {
                    "type": "string",
                    "description": "Date for historical data in YYYY-MM-DD format (defaults to today)",
                },
            },
            "required": ["target"],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Ahrefs API key not configured.")

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        }

        target = parameters["target"]
        date_str = parameters.get("date") or datetime.date.today().isoformat()
        params = {
            "target": target,
            "date": date_str,
        }
        url = "https://api.ahrefs.com/v3/site-explorer/domain-rating"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")