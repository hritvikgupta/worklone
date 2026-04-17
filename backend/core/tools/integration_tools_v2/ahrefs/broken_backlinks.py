from typing import Any, Dict
import httpx
import json
import os
from datetime import date
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class AhrefsBrokenBacklinksTool(BaseTool):
    name = "Ahrefs Broken Backlinks"
    description = "Get a list of broken backlinks pointing to a target domain or URL. Useful for identifying link reclamation opportunities."
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
        api_key = None
        if context is not None:
            api_key = context.get("AHREFS_API_KEY")
        if api_key is None:
            api_key = os.getenv("AHREFS_API_KEY")
        return api_key or ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "The target domain or URL to analyze. Example: \"example.com\" or \"https://example.com/page\"",
                },
                "mode": {
                    "type": "string",
                    "description": "Analysis mode: domain (entire domain), prefix (URL prefix), subdomains (include all subdomains), exact (exact URL match). Example: \"domain\"",
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
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Ahrefs API key not configured.")

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        }

        url = "https://api.ahrefs.com/v3/site-explorer/broken-backlinks"

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

                try:
                    data = response.json()
                except json.JSONDecodeError:
                    data = {}

                if response.status_code not in [200]:
                    error_msg = (
                        data.get("error", {}).get("message")
                        or data.get("error")
                        or response.text
                        or "Failed to get broken backlinks"
                    )
                    return ToolResult(success=False, output="", error=error_msg)

                backlinks = data.get("backlinks") or data.get("broken_backlinks") or []
                broken_backlinks = []
                for link in backlinks:
                    broken_backlinks.append({
                        "urlFrom": link.get("url_from") or "",
                        "urlTo": link.get("url_to") or "",
                        "httpCode": link.get("http_code") or link.get("status_code") or 404,
                        "anchor": link.get("anchor") or "",
                        "domainRatingSource": link.get("domain_rating_source") or link.get("domain_rating") or 0,
                    })
                output_data = {"brokenBacklinks": broken_backlinks}
                output_str = json.dumps(output_data)
                return ToolResult(success=True, output=output_str, data=output_data)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")