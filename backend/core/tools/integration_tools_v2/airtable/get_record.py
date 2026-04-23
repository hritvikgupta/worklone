from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class AirtableGetRecordTool(BaseTool):
    name = "airtable_get_record"
    description = "Retrieve a single record from an Airtable table by its ID"
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
                    "description": "Airtable base ID (starts with \"app\", e.g., \"appXXXXXXXXXXXXXX\")",
                },
                "tableId": {
                    "type": "string",
                    "description": "Table ID (starts with \"tbl\") or table name",
                },
                "recordId": {
                    "type": "string",
                    "description": "Record ID to retrieve (starts with \"rec\", e.g., \"recXXXXXXXXXXXXXX\")",
                },
            },
            "required": ["baseId", "tableId", "recordId"],
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
        record_id = parameters.get("recordId", "").strip()
        url = f"https://api.airtable.com/v0/{base_id}/{table_id}/{record_id}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200]:
                    data = response.json()
                    output_data = {
                        "record": data,
                        "metadata": {
                            "recordCount": 1,
                        },
                    }
                    return ToolResult(success=True, output=response.text, data=output_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")