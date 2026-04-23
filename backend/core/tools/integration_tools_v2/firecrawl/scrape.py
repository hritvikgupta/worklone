from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class FirecrawlScrapeTool(BaseTool):
    name = "firecrawl_scrape"
    description = "Extract structured content from web pages with comprehensive metadata support. Converts content to markdown or HTML while capturing SEO metadata, Open Graph tags, and page information."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="FIRECRAWL_API_KEY",
                description="Firecrawl API key",
                env_var="FIRECRAWL_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "firecrawl",
            context=context,
            context_token_keys=("apiKey",),
            env_token_keys=("FIRECRAWL_API_KEY",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to scrape content from (e.g., \"https://example.com/page\")",
                },
                "scrapeOptions": {
                    "type": "object",
                    "description": "Options for content scraping",
                },
            },
            "required": ["url"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = "https://api.firecrawl.dev/v2/scrape"
        
        body: Dict[str, Any] = {
            "url": parameters["url"],
        }
        scrape_options = parameters.get("scrapeOptions", {})
        body["formats"] = scrape_options.get("formats", ["markdown"])
        body.update(scrape_options)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    resp_data = response.json()
                    output_data = {
                        "markdown": resp_data.get("data", {}).get("markdown", ""),
                        "html": resp_data.get("data", {}).get("html", ""),
                        "metadata": resp_data.get("data", {}).get("metadata", {}),
                        "creditsUsed": resp_data.get("creditsUsed"),
                    }
                    return ToolResult(success=True, output=json.dumps(output_data), data=output_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")