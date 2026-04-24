from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class AttioQueryListEntriesTool(BaseTool):
    name = "attio_query_list_entries"
    description = "Query entries in an Attio list with optional filter, sort, and pagination"
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
                "list": {
                    "type": "string",
                    "description": "The list ID or slug",
                },
                "filter": {
                    "type": "string",
                    "description": "JSON filter object for querying entries",
                },
                "sorts": {
                    "type": "string",
                    "description": "JSON array of sort objects (e.g. [{\"attribute\":\"created_at\",\"direction\":\"desc\"}])",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of entries to return (default 500)",
                },
                "offset": {
                    "type": "number",
                    "description": "Number of entries to skip for pagination",
                },
            },
            "required": ["list"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = f"https://api.attio.com/v2/lists/{parameters['list'].strip()}/entries/query"
        
        body: Dict[str, Any] = {}
        filter_str = parameters.get("filter")
        if filter_str:
            try:
                body["filter"] = json.loads(filter_str)
            except json.JSONDecodeError:
                body["filter"] = {}
        sorts_str = parameters.get("sorts")
        if sorts_str:
            try:
                body["sorts"] = json.loads(sorts_str)
            except json.JSONDecodeError:
                body["sorts"] = []
        limit = parameters.get("limit")
        if limit is not None:
            body["limit"] = limit
        offset = parameters.get("offset")
        if offset is not None:
            body["offset"] = offset
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code not in [200, 201, 204]:
                    try:
                        err_data = response.json()
                        error_msg = err_data.get("message", "Failed to query list entries")
                    except:
                        error_msg = response.text
                    return ToolResult(success=False, output="", error=error_msg)
                
                data = response.json()
                entries = []
                for entry in data.get("data", []):
                    id_dict = entry.get("id", {})
                    entries.append({
                        "entryId": id_dict.get("entry_id"),
                        "listId": id_dict.get("list_id"),
                        "parentRecordId": entry.get("parent_record_id"),
                        "parentObject": entry.get("parent_object"),
                        "createdAt": entry.get("created_at"),
                        "entryValues": entry.get("entry_values", {}),
                    })
                result_data = {
                    "entries": entries,
                    "count": len(entries),
                }
                return ToolResult(success=True, output=json.dumps(result_data), data=result_data)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")