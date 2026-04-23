from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ApolloContactSearchTool(BaseTool):
    name = "apollo_contact_search"
    description = "Search your team's contacts in Apollo"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="APOLLO_API_KEY",
                description="Apollo API key",
                env_var="APOLLO_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "apollo",
            context=context,
            context_token_keys=("provider_token",),
            env_token_keys=("APOLLO_API_KEY",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "q_keywords": {
                    "type": "string",
                    "description": "Keywords to search for",
                },
                "contact_stage_ids": {
                    "type": "array",
                    "description": "Filter by contact stage IDs",
                },
                "page": {
                    "type": "number",
                    "description": "Page number for pagination (e.g., 1, 2, 3)",
                },
                "per_page": {
                    "type": "number",
                    "description": "Results per page, max 100 (e.g., 25, 50, 100)",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="API key not configured.")
        
        headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "X-Api-Key": access_token,
        }
        
        url = "https://api.apollo.io/api/v1/contacts/search"
        
        body: Dict[str, Any] = {
            "page": parameters.get("page") or 1,
            "per_page": min(parameters.get("per_page") or 25, 100),
        }
        q_keywords = parameters.get("q_keywords")
        if q_keywords:
            body["q_keywords"] = q_keywords
        contact_stage_ids = parameters.get("contact_stage_ids")
        if contact_stage_ids and len(contact_stage_ids) > 0:
            body["contact_stage_ids"] = contact_stage_ids
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")