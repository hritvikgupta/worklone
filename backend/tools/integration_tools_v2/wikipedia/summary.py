from typing import Any, Dict
import httpx
import urllib.parse
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class WikipediaSummaryTool(BaseTool):
    name = "wikipedia_summary"
    description = "Get a summary and metadata for a specific Wikipedia page."
    category = "integration"

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return []

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "pageTitle": {
                    "type": "string",
                    "description": "Title of the Wikipedia page to get summary for",
                },
            },
            "required": ["pageTitle"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        headers = {
            "User-Agent": "Sim/1.0 (https://sim.ai)",
            "Accept": "application/json",
        }

        page_title = parameters["pageTitle"]
        encoded_title = urllib.parse.quote(page_title.replace(" ", "_"))
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded_title}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")