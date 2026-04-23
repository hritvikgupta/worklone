from typing import Any, Dict
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class AshbySearchCandidatesTool(BaseTool):
    name = "ashby_search_candidates"
    description = "Searches for candidates by name and/or email with AND logic. Results are limited to 100 matches. Use candidate.list for full pagination."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="ashby_api_key",
                description="Ashby API Key",
                env_var="ASHBY_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "ashby",
            context=context,
            context_token_keys=("ashby_api_key", "api_key"),
            env_token_keys=("ASHBY_API_KEY",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Candidate name to search for (combined with email using AND logic)",
                },
                "email": {
                    "type": "string",
                    "description": "Candidate email to search for (combined with name using AND logic)",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Basic {base64.b64encode(f'{access_token}:'.encode()).decode()}",
            "Content-Type": "application/json",
        }
        
        body: Dict[str, Any] = {}
        if parameters.get("name"):
            body["name"] = parameters["name"]
        if parameters.get("email"):
            body["email"] = parameters["email"]
        
        url = "https://api.ashbyhq.com/candidate.search"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")