from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class AttioSearchRecordsTool(BaseTool):
    name = "attio_search_records"
    description = "Fuzzy search for records across object types in Attio"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="ATTIO_ACCESS_TOKEN",
                description="Access token",
                env_var="ATTIO_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "attio",
            context=context,
            context_token_keys=("provider_token",),
            env_token_keys=("ATTIO_ACCESS_TOKEN",),
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
                    "description": "The search query (max 256 characters)",
                },
                "objects": {
                    "type": "string",
                    "description": "Comma-separated object slugs to search (e.g. people,companies)",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of results (1-25, default 25)",
                },
            },
            "required": ["query", "objects"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = "https://api.attio.com/v2/objects/records/search"
        
        objects_str = parameters["objects"]
        objects_list = [s.strip() for s in objects_str.split(",") if s.strip()]
        body = {
            "query": parameters["query"],
            "objects": objects_list,
            "limit": int(parameters.get("limit", 25)),
            "request_as": {"type": "workspace"},
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")