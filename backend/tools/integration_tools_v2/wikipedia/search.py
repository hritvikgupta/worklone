import json
import httpx
from typing import Any, Dict
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class WikipediaSearchTool(BaseTool):
    name = "wikipedia_search"
    description = "Search for Wikipedia pages by title or content."
    category = "integration"

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return []

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query to find Wikipedia pages",
                },
                "searchLimit": {
                    "type": "number",
                    "description": "Maximum number of results to return (default: 10, max: 50)",
                },
            },
            "required": ["query"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        headers = {
            "User-Agent": "Sim/1.0 (https://sim.ai)",
            "Accept": "application/json",
        }
        base_url = "https://en.wikipedia.org/w/api.php"
        query_params = {
            "action": "opensearch",
            "search": parameters["query"],
            "format": "json",
            "namespace": "0",
        }
        search_limit = parameters.get("searchLimit")
        limit = 10
        if search_limit is not None:
            try:
                limit = min(int(search_limit), 50)
            except (ValueError, TypeError):
                limit = 10
        query_params["limit"] = str(limit)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(base_url, params=query_params, headers=headers)

                if response.status_code == 200:
                    data = response.json()
                    search_term = data[0] if len(data) > 0 else ""
                    titles = data[1] if len(data) > 1 else []
                    descriptions = data[2] if len(data) > 2 else []
                    urls = data[3] if len(data) > 3 else []

                    num_results = len(titles)
                    search_results = []
                    for index in range(num_results):
                        title = titles[index]
                        desc = descriptions[index] if index < len(descriptions) else ""
                        url_ = urls[index] if index < len(urls) else ""
                        search_results.append({
                            "id": index,
                            "key": title.replace(" ", "_"),
                            "title": title,
                            "excerpt": desc,
                            "matched_title": title,
                            "description": desc,
                            "thumbnail": None,
                            "url": url_,
                        })

                    transformed = {
                        "searchResults": search_results,
                        "totalHits": num_results,
                        "query": search_term,
                    }
                    output_str = json.dumps(transformed)
                    return ToolResult(success=True, output=output_str, data=transformed)
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")