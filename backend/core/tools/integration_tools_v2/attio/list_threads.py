from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class AttioListThreadsTool(BaseTool):
    name = "attio_list_threads"
    description = "List comment threads in Attio, optionally filtered by record or list entry"
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
            context_token_keys=("accessToken",),
            env_token_keys=("ATTIO_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "recordId": {
                    "type": "string",
                    "description": "Filter by record ID (requires object)",
                },
                "object": {
                    "type": "string",
                    "description": "Object slug to filter by (requires recordId)",
                },
                "entryId": {
                    "type": "string",
                    "description": "Filter by list entry ID (requires list)",
                },
                "list": {
                    "type": "string",
                    "description": "List ID or slug to filter by (requires entryId)",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of threads to return (max 50)",
                },
                "offset": {
                    "type": "number",
                    "description": "Number of threads to skip for pagination",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = "https://api.attio.com/v2/threads"
        params: Dict[str, str] = {}
        record_id = parameters.get("recordId")
        if record_id:
            params["record_id"] = record_id
        obj = parameters.get("object")
        if obj:
            params["object"] = obj
        entry_id = parameters.get("entryId")
        if entry_id:
            params["entry_id"] = entry_id
        lst = parameters.get("list")
        if lst:
            params["list"] = lst
        limit = parameters.get("limit")
        if limit is not None:
            params["limit"] = str(limit)
        offset = parameters.get("offset")
        if offset is not None:
            params["offset"] = str(offset)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")