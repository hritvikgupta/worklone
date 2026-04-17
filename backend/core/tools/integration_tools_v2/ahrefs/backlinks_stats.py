from typing import Any, Dict
import httpx
import os
from datetime import date
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class AhrefsBacklinksStatsTool(BaseTool):
    name = "ahrefs_backlinks_stats"
    description = """Get backlink statistics for a target domain or URL. Returns totals for different backlink types including dofollow, nofollow, text, image, and redirect links."""
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

    async def _resolve_api_key(self, context: dict | None) -> str:
        api_key = context.get("AHREFS_API_KEY") if context else None
        if self._is_placeholder_token(api_key or ""):
            api_key = os.getenv("AHREFS_API_KEY", "")
        return api_key

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": 'The target domain or URL to analyze. Example: "example.com" or "https://example.com/page"',
                },
                "mode": {
                    "type": "string",
                    "description": 'Analysis mode: domain (entire domain), prefix (URL prefix), subdomains (include all subdomains), exact (exact URL match). Example: "domain"',
                },
                "date": {
                    "type": "string",
                    "description": "Date for historical data in YYYY-MM-DD format (defaults to today)",
                },
            },
            "required": ["target"],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        api_key = await self._resolve_api_key(context)

        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Ahrefs API key not configured.")

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        base_url = "https://api.ahrefs.com/v3/site-explorer/backlinks-stats"
        query_params = {
            "target": parameters["target"],
        }
        date_str = parameters.get("date")
        if not date_str:
            date_str = date.today().isoformat()
        query_params["date"] = date_str
        if "mode" in parameters:
            query_params["mode"] = parameters["mode"]

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(base_url, headers=headers, params=query_params)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")