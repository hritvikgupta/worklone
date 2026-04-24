from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class AirtableUpdateMultipleRecordsTool(BaseTool):
    name = "airtable_update_multiple_records"
    description = "Update multiple existing records in an Airtable table"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="AIRTABLE_ACCESS_TOKEN",
                description="Airtable OAuth access token",
                env_var="AIRTABLE_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "airtable",
            context=context,
            context_token_keys=("provider_token",),
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
                    "description": "Airtable base ID (starts with \"app\", e.g., \"appXXXXXXXXXXXXXX\")",
                },
                "tableId": {
                    "type": "string",
                    "description": "Table ID (starts with \"tbl\") or table name",
                },
                "records": {
                    "type": "array",
                    "description": "Array of records to update, each with an `id` and a `fields` object",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {
                                "type": "string",
                                "description": "Record ID (starts with \"rec\")",
                            },
                            "fields": {
                                "type": "object",
                                "description": "Fields to update",
                                "additionalProperties": True,
                            },
                        },
                        "required": ["id", "fields"],
                    },
                },
            },
            "required": ["baseId", "tableId", "records"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        base_id = parameters.get("baseId", "").strip()
        table_id = parameters.get("tableId", "").strip()
        url = f"https://api.airtable.com/v0/{base_id}/{table_id}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(url, headers=headers, json={"records": parameters["records"]})
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")