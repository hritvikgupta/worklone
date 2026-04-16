from typing import Any, Dict
import httpx
import json
from datetime import date
from urllib.parse import urlencode
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class AhrefsOrganicKeywordsTool(BaseTool):
    name = "ahrefs_organic_keywords"
    description = "Get organic keywords that a target domain or URL ranks for in Google search results. Returns keyword details including search volume, ranking position, and estimated traffic."
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
                "target": {
                    "type": "string",
                    "description": "The target domain or URL to analyze. Example: \"example.com\" or \"https://example.com/page\"",
                },
                "country": {
                    "type": "string",
                    "description": "Country code for search results. Example: \"us\", \"gb\", \"de\" (default: \"us\")",
                },
                "mode": {
                    "type": "string",
                    "description": "Analysis mode: domain (entire domain), prefix (URL prefix), subdomains (include all subdomains), exact (exact URL match). Example: \"domain\"",
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
            },
            "required": ["target"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("AHREFS_API_KEY") if context else None
        if self._is_placeholder_token(api_key or ""):
            return ToolResult(success=False, output="", error="Ahrefs API key not configured.")

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        today = date.today().isoformat()
        date_param = parameters.get("date", today)
        params_dict = {
            "target": parameters["target"],
            "country": parameters.get("country", "us"),
            "date": date_param,
        }
        if "mode" in parameters:
            params_dict["mode"] = parameters["mode"]
        if "limit" in parameters:
            params_dict["limit"] = parameters["limit"]
        if "offset" in parameters:
            params_dict["offset"] = parameters["offset"]

        url = "https://api.ahrefs.com/v3/site-explorer/organic-keywords?" + urlencode(params_dict)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if 200 <= response.status_code < 300:
                    data = response.json()
                    raw_keywords = data.get("keywords") or data.get("organic_keywords") or []
                    keywords = [
                        {
                            "keyword": kw.get("keyword") or "",
                            "volume": kw.get("volume", 0),
                            "position": kw.get("position", 0),
                            "url": kw.get("url") or "",
                            "traffic": kw.get("traffic", 0),
                            "keywordDifficulty": kw.get("keyword_difficulty") or kw.get("difficulty") or 0,
                        }
                        for kw in raw_keywords
                    ]
                    transformed = {"keywords": keywords}
                    return ToolResult(
                        success=True,
                        output=json.dumps(transformed),
                        data=transformed,
                    )
                else:
                    try:
                        error_data = response.json()
                        error_msg = (
                            error_data.get("error", {}).get("message")
                            or error_data.get("error")
                            or response.text
                        )
                    except Exception:
                        error_msg = response.text
                    return ToolResult(success=False, output="", error=error_msg)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")