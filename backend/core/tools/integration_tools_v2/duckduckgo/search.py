from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class DuckDuckGoSearchTool(BaseTool):
    name = "duckduckgo_search"
    description = "Search the web using DuckDuckGo Instant Answers API. Returns instant answers, abstracts, and related topics for your query. Free to use without an API key."
    category = "integration"

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return []

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to execute",
                },
                "noHtml": {
                    "type": "boolean",
                    "description": "Remove HTML from text in results (default: true)",
                },
                "skipDisambig": {
                    "type": "boolean",
                    "description": "Skip disambiguation results (default: false)",
                },
            },
            "required": ["query"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        headers = {
            "Accept": "application/json",
        }
        url = "https://api.duckduckgo.com/"
        params: Dict[str, str] = {
            "q": parameters["query"],
            "format": "json",
            "no_html": "1" if parameters.get("noHtml") is not False else "0",
            "skip_disambig": "1" if parameters.get("skipDisambig") else "0",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params, headers=headers)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")