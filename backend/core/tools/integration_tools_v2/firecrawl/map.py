from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class FirecrawlMapTool(BaseTool):
    name = "firecrawl_map"
    description = "Get a complete list of URLs from any website quickly and reliably. Useful for discovering all pages on a site without crawling them."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="apiKey",
                description="Firecrawl API key",
                env_var="FIRECRAWL_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        return context.get("apiKey", "") if context else ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The base URL to map and discover links from (e.g., \"https://example.com\")",
                },
                "search": {
                    "type": "string",
                    "description": "Filter results by relevance to a search term (e.g., \"blog\")",
                },
                "sitemap": {
                    "type": "string",
                    "description": "Controls sitemap usage: \"skip\", \"include\" (default), or \"only\"",
                },
                "includeSubdomains": {
                    "type": "boolean",
                    "description": "Whether to include URLs from subdomains (default: true)",
                },
                "ignoreQueryParameters": {
                    "type": "boolean",
                    "description": "Exclude URLs containing query strings (default: true)",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of links to return (e.g., 100, 1000, 5000). Max: 100,000, default: 5,000",
                },
                "timeout": {
                    "type": "number",
                    "description": "Request timeout in milliseconds",
                },
            },
            "required": ["url"],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        url = "https://api.firecrawl.dev/v2/map"

        body = {"url": parameters["url"]}
        if parameters.get("search"):
            body["search"] = parameters["search"]
        if parameters.get("sitemap"):
            body["sitemap"] = parameters["sitemap"]
        if "includeSubdomains" in parameters:
            body["includeSubdomains"] = parameters["includeSubdomains"]
        if "ignoreQueryParameters" in parameters:
            body["ignoreQueryParameters"] = parameters["ignoreQueryParameters"]
        if parameters.get("limit"):
            body["limit"] = int(parameters["limit"])
        if parameters.get("timeout"):
            body["timeout"] = int(parameters["timeout"])

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")