from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class ParallelSearchTool(BaseTool):
    name = "parallel_search"
    description = "Search the web using Parallel AI. Provides comprehensive search results with intelligent processing and content extraction."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="PARALLEL_API_KEY",
                description="Parallel AI API Key",
                env_var="PARALLEL_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "objective": {
                    "type": "string",
                    "description": "The search objective or question to answer",
                },
                "search_queries": {
                    "type": "string",
                    "description": "Comma-separated list of search queries to execute",
                },
                "mode": {
                    "type": "string",
                    "description": "Search mode: one-shot, agentic, or fast (default: one-shot)",
                },
                "max_results": {
                    "type": "number",
                    "description": "Maximum number of results to return (default: 10)",
                },
                "max_chars_per_result": {
                    "type": "number",
                    "description": "Maximum characters per result excerpt (minimum: 1000)",
                },
                "include_domains": {
                    "type": "string",
                    "description": "Comma-separated list of domains to restrict search results to",
                },
                "exclude_domains": {
                    "type": "string",
                    "description": "Comma-separated list of domains to exclude from search results",
                },
            },
            "required": ["objective"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("PARALLEL_API_KEY") if context else None

        if self._is_placeholder_token(api_key or ""):
            return ToolResult(success=False, output="", error="API key not configured.")

        body: dict[str, Any] = {
            "objective": parameters["objective"],
        }

        search_queries = parameters.get("search_queries")
        if search_queries:
            queries = [q.strip() for q in str(search_queries).split(",") if q.strip()]
            if queries:
                body["search_queries"] = queries

        mode = parameters.get("mode")
        if mode:
            body["mode"] = mode

        max_results = parameters.get("max_results")
        if max_results is not None:
            body["max_results"] = int(max_results)

        max_chars_per_result = parameters.get("max_chars_per_result")
        if max_chars_per_result is not None:
            body["excerpts"] = {"max_chars_per_result": int(max_chars_per_result)}

        source_policy: dict[str, list[str]] = {}
        include_domains = parameters.get("include_domains")
        if include_domains:
            domains = [d.strip() for d in str(include_domains).split(",") if d.strip()]
            if domains:
                source_policy["include_domains"] = domains

        exclude_domains = parameters.get("exclude_domains")
        if exclude_domains:
            domains = [d.strip() for d in str(exclude_domains).split(",") if d.strip()]
            if domains:
                source_policy["exclude_domains"] = domains

        if source_policy:
            body["source_policy"] = source_policy

        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "parallel-beta": "search-extract-2025-10-10",
        }

        url = "https://api.parallel.ai/v1beta/search"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")