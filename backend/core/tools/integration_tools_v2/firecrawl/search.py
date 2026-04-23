from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class FirecrawlSearchTool(BaseTool):
    name = "firecrawl_search"
    description = "Search for information on the web using Firecrawl"
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
            context_token_keys=("apiKey",},
            env_token_keys=("FIRECRAWL_API_KEY",},
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
                    "description": "The search query to use",
                },
                "limit": {
                    "type": "integer",
                },
                "sources": {
                    "type": "array",
                    "items": {
                        "type": "string",
                    },
                },
                "categories": {
                    "type": "array",
                    "items": {
                        "type": "string",
                    },
                },
                "tbs": {
                    "type": "string",
                },
                "location": {
                    "type": "string",
                },
                "country": {
                    "type": "string",
                },
                "timeout": {
                    "type": "integer",
                },
                "ignoreInvalidURLs": {
                    "type": "boolean",
                },
                "scrapeOptions": {
                    "type": "object",
                },
            },
            "required": ["query"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = "https://api.firecrawl.dev/v2/search"
        
        body: Dict[str, Any] = {
            "query": parameters["query"],
        }
        
        optional_keys = [
            "limit",
            "sources",
            "categories",
            "tbs",
            "location",
            "country",
            "timeout",
            "scrapeOptions",
        ]
        for key in optional_keys:
            if key in parameters and parameters[key]:
                if key in ("limit", "timeout"):
                    body[key] = int(parameters[key])
                else:
                    body[key] = parameters[key]
        
        if "ignoreInvalidURLs" in parameters and isinstance(parameters["ignoreInvalidURLs"], bool):
            body["ignoreInvalidURLs"] = parameters["ignoreInvalidURLs"]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")