from typing import Any, Dict, List
import httpx
import time
import asyncio
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class FirecrawlCrawlTool(BaseTool):
    name = "firecrawl_crawl"
    description = "Crawl entire websites and extract structured content from all accessible pages"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="FIRECRAWL_API_KEY",
                description="Firecrawl API Key",
                env_var="FIRECRAWL_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The website URL to crawl (e.g., \"https://example.com\" or \"https://docs.example.com/guide\")",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of pages to crawl (e.g., 50, 100, 500). Default: 100",
                },
                "maxDepth": {
                    "type": "number",
                    "description": "Maximum depth to crawl from the starting URL (e.g., 1, 2, 3). Controls how many levels deep to follow links",
                },
                "formats": {
                    "type": "array",
                    "items": {
                        "type": "string",
                    },
                    "description": "Output formats for scraped content (e.g., [\"markdown\"], [\"markdown\", \"html\"], [\"markdown\", \"links\"])",
                },
                "excludePaths": {
                    "type": "array",
                    "items": {
                        "type": "string",
                    },
                    "description": "URL paths to exclude from crawling (e.g., [\"/blog/*\", \"/admin/*\", \"/*.pdf\"])",
                },
                "includePaths": {
                    "type": "array",
                    "items": {
                        "type": "string",
                    },
                    "description": "URL paths to include in crawling (e.g., [\"/docs/*\", \"/api/*\"]). Only these paths will be crawled",
                },
                "onlyMainContent": {
                    "type": "boolean",
                    "description": "Extract only main content from pages",
                },
            },
            "required": ["url"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("FIRECRAWL_API_KEY") if context else None
        
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Firecrawl API key not configured.")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        body: Dict[str, Any] = {
            "url": parameters["url"],
            "limit": int(parameters.get("limit", 100)),
            "scrapeOptions": {
                "formats": parameters.get("formats", ["markdown"]),
                "onlyMainContent": parameters.get("onlyMainContent", False),
            },
        }
        if parameters.get("maxDepth") is not None:
            body["maxDiscoveryDepth"] = int(parameters["maxDepth"])
        if parameters.get("excludePaths") is not None:
            body["excludePaths"] = parameters["excludePaths"]
        if parameters.get("includePaths") is not None:
            body["includePaths"] = parameters["includePaths"]
        
        poll_interval = 5.0
        max_poll_time = 300.0  # 5 minutes
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post("https://api.firecrawl.dev/v2/crawl", headers=headers, json=body)
                response.raise_for_status()
                data = response.json()
                job_id = data.get("jobId") or data.get("id")
                if not job_id:
                    return ToolResult(success=False, output="", error="No job ID returned from Firecrawl API.")
                
                start_time = time.time()
                
                while True:
                    elapsed = time.time() - start_time
                    if elapsed > max_poll_time:
                        return ToolResult(
                            success=False,
                            output="",
                            error=f"Crawl job did not complete within {max_poll_time / 60:.0f} minutes",
                        )
                    
                    poll_url = f"https://api.firecrawl.dev/v2/crawl/{job_id}"
                    poll_response = await client.get(poll_url, headers=headers)
                    poll_response.raise_for_status()
                    crawl_data = poll_response.json()
                    status = crawl_data.get("status")
                    
                    if status == "completed":
                        output_data = {
                            "pages": crawl_data.get("data", []),
                            "total": crawl_data.get("total", 0),
                            "creditsUsed": crawl_data.get("creditsUsed", 0),
                        }
                        output_str = json.dumps(output_data, indent=2)
                        return ToolResult(success=True, output=output_str, data=output_data)
                    
                    if status == "failed":
                        error_msg = crawl_data.get("error", "Unknown error")
                        return ToolResult(
                            success=False,
                            output="",
                            error=f"Crawl job failed: {error_msg}",
                        )
                    
                    await asyncio.sleep(poll_interval)
                    
        except httpx.HTTPStatusError as e:
            return ToolResult(success=False, output="", error=f"API error: {e.response.text}")
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")