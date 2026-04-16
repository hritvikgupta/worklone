import os
import httpx
from datetime import date
from typing import Dict, Any
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class AhrefsReferringDomainsTool(BaseTool):
    name = "ahrefs_referring_domains"
    description = "Get a list of domains that link to a target domain or URL. Returns unique referring domains with their domain rating, backlink counts, and discovery dates."
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
        if api_key is None:
            api_key = os.getenv("AHREFS_API_KEY")
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
                "limit": {
                    "type": "number",
                    "description": "Maximum number of results to return. Example: 50 (default: 100)",
                },
                "offset": {
                    "type": "number",
                    "description": "Number of results to skip for pagination. Example: 100",
                },
            },
            "required": ["target"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = await self._resolve_api_key(context)

        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Ahrefs API key not configured.")

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        url = "https://api.ahrefs.com/v3/site-explorer/refdomains"

        params_dict: Dict[str, Any] = {
            "target": parameters["target"],
        }
        date_str = parameters.get("date")
        if not date_str:
            date_str = date.today().isoformat()
        params_dict["date"] = date_str

        mode = parameters.get("mode")
        if mode:
            params_dict["mode"] = mode

        limit = parameters.get("limit")
        if limit is not None:
            params_dict["limit"] = limit

        offset = parameters.get("offset")
        if offset is not None:
            params_dict["offset"] = offset

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params_dict)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")