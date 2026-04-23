from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ExaGetContentsTool(BaseTool):
    name = "exa_get_contents"
    description = "Retrieve the contents of webpages using Exa AI. Returns the title, text content, and optional summaries for each URL."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="EXA_API_KEY",
                description="Exa AI API Key",
                env_var="EXA_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "exa",
            context=context,
            context_token_keys=("apiKey",),
            env_token_keys=("EXA_API_KEY",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "urls": {
                    "type": "string",
                    "description": "Comma-separated list of URLs to retrieve content from",
                },
                "text": {
                    "type": "boolean",
                    "description": "If true, returns full page text with default settings. If false, disables text return.",
                },
                "summaryQuery": {
                    "type": "string",
                    "description": "Query to guide the summary generation",
                },
                "subpages": {
                    "type": "number",
                    "description": "Number of subpages to crawl from the provided URLs",
                },
                "subpageTarget": {
                    "type": "string",
                    "description": "Comma-separated keywords to target specific subpages (e.g., \"docs,tutorial,about\")",
                },
                "highlights": {
                    "type": "boolean",
                    "description": "Include highlighted snippets in results (default: false)",
                },
                "livecrawl": {
                    "type": "string",
                    "description": "Live crawling mode: never (default), fallback, always, or preferred (always try livecrawl, fall back to cache if fails)",
                },
            },
            "required": ["urls"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": access_token,
        }
        
        urls_string = parameters["urls"]
        url_array = [url.strip() for url in urls_string.split(",") if url.strip()]
        body: Dict[str, Any] = {
            "urls": url_array,
        }
        text = parameters.get("text")
        if text is not None:
            body["text"] = text
        summary_query = parameters.get("summaryQuery")
        if summary_query:
            body["summary"] = {"query": summary_query}
        subpages = parameters.get("subpages")
        if subpages is not None:
            body["subpages"] = int(subpages)
        subpage_target = parameters.get("subpageTarget")
        if subpage_target:
            body["subpageTarget"] = [t.strip() for t in subpage_target.split(",") if t.strip()]
        highlights = parameters.get("highlights")
        if highlights is not None:
            body["highlights"] = highlights
        livecrawl = parameters.get("livecrawl")
        if livecrawl:
            body["livecrawl"] = livecrawl
        
        url = "https://api.exa.ai/contents"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")