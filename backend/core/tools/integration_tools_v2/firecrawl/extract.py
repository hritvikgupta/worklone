from typing import Any, Dict
import httpx
import asyncio
import os
import time
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class FirecrawlExtractTool(BaseTool):
    name = "firecrawl_extract"
    description = "Extract structured data from entire webpages using natural language prompts and JSON schema. Powerful agentic feature for intelligent data extraction."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="firecrawl_api_key",
                description="Firecrawl API key",
                env_var="FIRECRAWL_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_api_key(self, context: dict | None) -> str:
        api_key = ""
        if context:
            api_key = context.get("firecrawl_api_key", "")
        if not api_key:
            api_key = os.getenv("FIRECRAWL_API_KEY", "")
        return api_key

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "urls": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": 'Array of URLs to extract data from (e.g., ["https://example.com/page1", "https://example.com/page2"] or ["https://example.com/*"])',
                },
                "prompt": {
                    "type": "string",
                    "description": "Natural language guidance for the extraction process",
                },
                "schema": {
                    "type": "object",
                    "description": "JSON Schema defining the structure of data to extract",
                },
                "enableWebSearch": {
                    "type": "boolean",
                    "description": "Enable web search to find supplementary information (default: false)",
                },
                "ignoreSitemap": {
                    "type": "boolean",
                    "description": "Ignore sitemap.xml files during scanning (default: false)",
                },
                "includeSubdomains": {
                    "type": "boolean",
                    "description": "Extend scanning to subdomains (default: true)",
                },
                "showSources": {
                    "type": "boolean",
                    "description": "Return data sources in the response (default: false)",
                },
                "ignoreInvalidURLs": {
                    "type": "boolean",
                    "description": "Skip invalid URLs in the array (default: true)",
                },
                "scrapeOptions": {
                    "type": "object",
                    "description": "Advanced scraping configuration options",
                },
            },
            "required": ["urls"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = await self._resolve_api_key(context)

        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Firecrawl API key not configured.")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        body: Dict[str, Any] = {"urls": parameters["urls"]}
        optional_keys = [
            "prompt",
            "schema",
            "enableWebSearch",
            "ignoreSitemap",
            "includeSubdomains",
            "showSources",
            "ignoreInvalidURLs",
        ]
        for key in optional_keys:
            if key in parameters:
                body[key] = parameters[key]
        if "scrapeOptions" in parameters:
            scrape_options = parameters["scrapeOptions"]
            if isinstance(scrape_options, dict):
                cleaned_scrape_options = {k: v for k, v in scrape_options.items() if v is not None}
                if cleaned_scrape_options:
                    body["scrapeOptions"] = cleaned_scrape_options

        url = "https://api.firecrawl.dev/v2/extract"

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code not in [200, 201]:
                    return ToolResult(success=False, output="", error=response.text)

                data = response.json()
                job_id = data.get("id")
                if not job_id:
                    return ToolResult(success=False, output="", error="No job ID returned from extract API.")

                poll_interval = 5.0
                max_poll_time = 300.0  # 5 minutes
                start_time = time.time()

                while True:
                    elapsed = time.time() - start_time
                    if elapsed > max_poll_time:
                        return ToolResult(
                            success=False,
                            output="",
                            error=f"Extract job did not complete within the maximum polling time ({max_poll_time / 1000:.0f}s)",
                        )

                    status_url = f"https://api.firecrawl.dev/v2/extract/{job_id}"
                    status_response = await client.get(status_url, headers=headers)

                    if status_response.status_code != 200:
                        return ToolResult(success=False, output="", error=status_response.text)

                    extract_data = status_response.json()
                    status = extract_data.get("status")

                    if status == "completed":
                        return ToolResult(
                            success=True,
                            output=status_response.text,
                            data=extract_data,
                        )
                    elif status == "failed":
                        error_msg = extract_data.get("error", "Unknown error")
                        return ToolResult(
                            success=False,
                            output="",
                            error=f"Extract job failed: {error_msg}",
                        )

                    await asyncio.sleep(poll_interval)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")