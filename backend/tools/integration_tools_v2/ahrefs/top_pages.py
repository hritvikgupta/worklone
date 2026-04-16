from typing import Any, Dict
import httpx
import os
from datetime import date
from urllib.parse import urlencode
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class AhrefsTopPagesTool(BaseTool):
    name = "ahrefs_top_pages"
    description = "Get the top pages of a target domain sorted by organic traffic. Returns page URLs with their traffic, keyword counts, and estimated traffic value."
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

    def _get_api_key(self, context: dict | None) -> str:
        api_key = (context or {}).get("AHREFS_API_KEY") or os.getenv("AHREFS_API_KEY", "")
        return api_key.strip()

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": 'The target domain to analyze. Example: "example.com"',
                },
                "country": {
                    "type": "string",
                    "description": 'Country code for traffic data. Example: "us", "gb", "de" (default: "us")',
                },
                "mode": {
                    "type": "string",
                    "description": 'Analysis mode: domain (entire domain), prefix (URL prefix), subdomains (include all subdomains). Example: "domain"',
                },
                "date": {
                    "type": "string",
                    "description": "Date for historical data in YYYY-MM-DD format (defaults to today)",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of results to return. Example: 50 (default: 100)",
                },
                "offset": {
                    "type": "number",
                    "description": "Number of results to skip for pagination. Example: 100",
                },
                "select": {
                    "type": "string",
                    "description": 'Comma-separated list of fields to return (e.g., url,traffic,keywords,top_keyword,value). Default: url,traffic,keywords,top_keyword,value',
                },
            },
            "required": ["target"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = self._get_api_key(context)

        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Ahrefs API key not configured.")

        query_params = {
            "target": parameters["target"],
            "country": parameters.get("country", "us"),
            "date": parameters.get("date") or date.today().isoformat(),
            "select": parameters.get("select", "url,traffic,keywords,top_keyword,value"),
        }
        if parameters.get("mode"):
            query_params["mode"] = parameters["mode"]
        if parameters.get("limit") is not None:
            query_params["limit"] = str(parameters["limit"])
        if parameters.get("offset") is not None:
            query_params["offset"] = str(parameters["offset"])

        url = f"https://api.ahrefs.com/v3/site-explorer/top-pages?{urlencode(query_params)}"

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code != 200:
                    try:
                        err_data = response.json()
                        error_msg = (
                            err_data.get("error", {}).get("message")
                            or err_data.get("error")
                            or response.text
                        )
                    except Exception:
                        error_msg = response.text
                    return ToolResult(success=False, output="", error=error_msg)

                data = response.json()
                pages = []
                for page in data.get("pages") or data.get("top_pages") or []:
                    pages.append({
                        "url": page.get("url", ""),
                        "traffic": page.get("traffic", 0),
                        "keywords": page.get("keywords") or page.get("keyword_count", 0),
                        "topKeyword": page.get("top_keyword", ""),
                        "value": page.get("value") or page.get("traffic_value", 0),
                    })
                result = {"pages": pages}
                return ToolResult(success=True, output=result, data=result)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")