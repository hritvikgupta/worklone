from typing import Any, Dict
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ExaFindSimilarLinksTool(BaseTool):
    name = "exa_find_similar_links"
    description = "Find webpages similar to a given URL using Exa AI. Returns a list of similar links with titles and text snippets."
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
            context_token_keys=("apiKey",},
            env_token_keys=("EXA_API_KEY",},
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
                    "description": "The URL to find similar links for",
                },
                "numResults": {
                    "type": "number",
                    "description": "Number of similar links to return (e.g., 5, 10, 25). Default: 10, max: 25",
                },
                "text": {
                    "type": "boolean",
                    "description": "Whether to include the full text of the similar pages",
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
            "required": ["url"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": access_token,
        }
        
        body: dict = {"url": parameters["url"]}
        
        if "numResults" in parameters and parameters["numResults"]:
            body["numResults"] = int(parameters["numResults"])
        
        if "includeDomains" in parameters and parameters["includeDomains"]:
            body["includeDomains"] = [d.strip() for d in parameters["includeDomains"].split(",") if d.strip()]
        
        if "excludeDomains" in parameters and parameters["excludeDomains"]:
            body["excludeDomains"] = [d.strip() for d in parameters["excludeDomains"].split(",") if d.strip()]
        
        contents: dict = {}
        if "text" in parameters:
            contents["text"] = parameters["text"]
        
        if contents:
            body["contents"] = contents
        
        url = "https://api.exa.ai/findSimilar"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")