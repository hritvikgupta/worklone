from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ExaSearchTool(BaseTool):
    name = "exa_search"
    description = "Search the web using Exa AI. Returns relevant search results with titles, URLs, and text snippets."
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
                "query": {
                    "type": "string",
                    "description": "The search query to execute",
                },
                "numResults": {
                    "type": "number",
                    "description": "Number of results to return (e.g., 5, 10, 25). Default: 10, max: 25",
                },
                "useAutoprompt": {
                    "type": "boolean",
                    "description": "Whether to use autoprompt to improve the query (true or false). Default: false",
                },
                "type": {
                    "type": "string",
                    "description": 'Search type: "neural", "keyword", "auto", or "fast". Default: "auto"',
                },
                "includeDomains": {
                    "type": "string",
                    "description": 'Comma-separated list of domains to include in results (e.g., "github.com, stackoverflow.com")',
                },
                "excludeDomains": {
                    "type": "string",
                    "description": 'Comma-separated list of domains to exclude from results (e.g., "reddit.com, pinterest.com")',
                },
            },
            "required": ["query"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = await self._resolve_access_token(context)

        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
        }

        url = "https://api.exa.ai/search"

        body = {
            "query": parameters["query"],
        }

        num_results = parameters.get("numResults")
        if num_results is not None:
            body["numResults"] = int(num_results)

        use_autoprompt = parameters.get("useAutoprompt")
        if use_autoprompt is not None:
            body["useAutoprompt"] = use_autoprompt

        search_type = parameters.get("type")
        if search_type:
            body["type"] = search_type

        include_domains = parameters.get("includeDomains")
        if include_domains:
            body["includeDomains"] = [d.strip() for d in include_domains.split(",") if d.strip()]

        exclude_domains = parameters.get("excludeDomains")
        if exclude_domains:
            body["excludeDomains"] = [d.strip() for d in exclude_domains.split(",") if d.strip()]

        category = parameters.get("category")
        if category:
            body["category"] = category

        contents: Dict[str, Any] = {}
        text = parameters.get("text")
        if text is not None:
            contents["text"] = text

        highlights = parameters.get("highlights")
        if highlights is not None:
            contents["highlights"] = highlights

        summary_ = parameters.get("summary")
        if summary_ is not None:
            contents["summary"] = summary_

        livecrawl = parameters.get("livecrawl")
        if livecrawl:
            contents["livecrawl"] = livecrawl

        if contents:
            body["contents"] = contents

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")