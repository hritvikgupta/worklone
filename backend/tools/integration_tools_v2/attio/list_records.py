from typing import Any, Dict
import httpx
import json
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class AttioListRecordsTool(BaseTool):
    name = "attio_list_records"
    description = "Query and list records for a given object type (e.g. people, companies)"
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
            context_token_keys=("attio_token",),
            env_token_keys=("ATTIO_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "objectType": {
                    "type": "string",
                    "description": "The object type slug (e.g. people, companies)",
                },
                "filter": {
                    "type": "string",
                    "description": "JSON filter object for querying records",
                },
                "sorts": {
                    "type": "string",
                    "description": "JSON array of sort objects, e.g. [{'direction':'asc','attribute':'name'}]",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of records to return (default 500)",
                },
                "offset": {
                    "type": "number",
                    "description": "Number of records to skip for pagination",
                },
            },
            "required": ["objectType"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        object_type = parameters.get("objectType", "").strip()
        if not object_type:
            return ToolResult(success=False, output="", error="objectType is required.")
        
        url = f"https://api.attio.com/v2/objects/{object_type}/records/query"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        body: Dict[str, Any] = {}
        filter_str = parameters.get("filter")
        if filter_str:
            try:
                body["filter"] = json.loads(filter_str)
            except json.JSONDecodeError:
                body["filter"] = filter_str
        sorts_str = parameters.get("sorts")
        if sorts_str:
            try:
                body["sorts"] = json.loads(sorts_str)
            except json.JSONDecodeError:
                body["sorts"] = sorts_str
        limit = parameters.get("limit")
        if limit is not None:
            body["limit"] = limit
        offset = parameters.get("offset")
        if offset is not None:
            body["offset"] = offset
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    try:
                        data = response.json()
                        records = data.get("data", []) if isinstance(data, dict) else []
                        output_data = {
                            "records": records,
                            "count": len(records),
                        }
                        return ToolResult(success=True, output=str(output_data), data=output_data)
                    except json.JSONDecodeError:
                        return ToolResult(success=True, output=response.text, data={})
                else:
                    try:
                        err_data = response.json()
                        error_msg = err_data.get("message", response.text) if isinstance(err_data, dict) else response.text
                    except json.JSONDecodeError:
                        error_msg = response.text
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")