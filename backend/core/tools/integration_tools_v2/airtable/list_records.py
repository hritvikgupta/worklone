from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class AirtableListRecordsTool(BaseTool):
    name = "airtable_list_records"
    description = "Read records from an Airtable table"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="AIRTABLE_ACCESS_TOKEN",
                description="Access token",
                env_var="AIRTABLE_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "airtable",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("AIRTABLE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "baseId": {
                    "type": "string",
                    "description": 'Airtable base ID (starts with "app", e.g., "appXXXXXXXXXXXXXX")',
                },
                "tableId": {
                    "type": "string",
                    "description": 'Table ID (starts with "tbl") or table name',
                },
                "maxRecords": {
                    "type": "number",
                    "description": "Maximum number of records to return (default: all records)",
                },
                "filterFormula": {
                    "type": "string",
                    "description": 'Formula to filter records (e.g., "({Field Name} = \\'Value\\')")',
                },
            },
            "required": ["baseId", "tableId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        base_id = parameters["baseId"].strip()
        table_id = parameters["tableId"].strip()
        url = f"https://api.airtable.com/v0/{base_id}/{table_id}"
        
        params: Dict[str, str] = {}
        if parameters.get("maxRecords") is not None:
            params["maxRecords"] = str(int(parameters["maxRecords"]))
        if parameters.get("filterFormula"):
            params["filterByFormula"] = parameters["filterFormula"]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params)
                
                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    transformed = {
                        "records": data.get("records", []),
                        "metadata": {
                            "offset": data.get("offset"),
                            "totalRecords": len(data.get("records", [])),
                        },
                    }
                    return ToolResult(success=True, output=json.dumps(transformed), data=transformed)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")