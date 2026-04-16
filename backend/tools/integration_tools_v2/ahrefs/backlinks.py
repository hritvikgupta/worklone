from typing import Any, Dict
import httpx
import json
from datetime import date
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class AhrefsBacklinksTool(BaseTool):
    name = "ahrefs_backlinks"
    description = "Get a list of backlinks pointing to a target domain or URL. Returns details about each backlink including source URL, anchor text, and domain rating."
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

        params: Dict[str, str | int | float] = {
            "target": parameters["target"],
            "date": parameters.get("date") or date.today().isoformat(),
        }
        mode = parameters.get("mode")
        if mode:
            params["mode"] = mode
        limit = parameters.get("limit")
        if limit is not None:
            params["limit"] = limit
        offset = parameters.get("offset")
        if offset is not None:
            params["offset"] = offset

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    "https://api.ahrefs.com/v3/site-explorer/backlinks",
                    headers=headers,
                    params=params,
                )

            if response.status_code == 200:
                data = response.json()
                backlinks = []
                for link in data.get("backlinks", []):
                    backlinks.append({
                        "urlFrom": link.get("url_from") or "",
                        "urlTo": link.get("url_to") or "",
                        "anchor": link.get("anchor") or "",
                        "domainRatingSource": link.get("domain_rating_source") or link.get("domain_rating") or 0,
                        "isDofollow": link.get("is_dofollow") or link.get("dofollow") or False,
                        "firstSeen": link.get("first_seen") or "",
                        "lastVisited": link.get("last_visited") or "",
                    })
                output_data = {"backlinks": backlinks}
                return ToolResult(
                    success=True,
                    output=json.dumps(output_data),
                    data=output_data,
                )
            else:
                error_data = {}
                try:
                    error_data = response.json()
                except Exception:
                    pass
                error_msg = (
                    error_data.get("error", {}).get("message")
                    or error_data.get("error")
                    or "Failed to get backlinks"
                )
                return ToolResult(
                    success=False,
                    output="",
                    error=error_msg,
                )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")