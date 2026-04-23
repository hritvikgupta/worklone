from typing import Any, Dict
import httpx
import json
import time
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class IntercomSearchConversationsTool(BaseTool):
    name = "Search Conversations in Intercom"
    description = "Search for conversations in Intercom using a query. Returns API-aligned fields only."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="INTERCOM_ACCESS_TOKEN",
                description="Intercom API access token",
                env_var="INTERCOM_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "intercom",
            context=context,
            context_token_keys=("access_token",),
            env_token_keys=("INTERCOM_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query as JSON object",
                },
                "per_page": {
                    "type": "number",
                    "description": "Number of results per page (max: 150)",
                },
                "starting_after": {
                    "type": "string",
                    "description": "Cursor for pagination",
                },
                "sort_field": {
                    "type": "string",
                    "description": 'Field to sort by (e.g., "created_at", "updated_at")',
                },
                "sort_order": {
                    "type": "string",
                    "description": 'Sort order: "ascending" or "descending"',
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
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Intercom-Version": "2.14",
        }
        
        url = "https://api.intercom.io/conversations/search"
        
        try:
            try:
                query_dict = json.loads(parameters["query"])
            except (json.JSONDecodeError, KeyError, TypeError):
                query_dict = {
                    "field": "updated_at",
                    "operator": ">",
                    "value": int(time.time()) - 86400,
                }
            
            body: Dict[str, Any] = {"query": query_dict}
            
            pagination: Dict[str, Any] = {}
            per_page = parameters.get("per_page")
            if per_page is not None:
                pagination["per_page"] = per_page
            starting_after = parameters.get("starting_after")
            if starting_after is not None:
                pagination["starting_after"] = starting_after
            if pagination:
                body["pagination"] = pagination
            
            sort_field = parameters.get("sort_field")
            if sort_field is not None:
                body["sort"] = {
                    "field": sort_field,
                    "order": parameters.get("sort_order", "descending"),
                }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")