from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class AirtableListTablesTool(BaseTool):
    name = "airtable_list_tables"
    description = "List all tables and their schema in an Airtable base"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="AIRTABLE_ACCESS_TOKEN",
                description="OAuth access token",
                env_var="AIRTABLE_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "airtable",
            context=context,
            context_token_keys=("airtable_access_token",),
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
            },
            "required": ["baseId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        base_id = (parameters.get("baseId") or "").strip()
        url = f"https://api.airtable.com/v0/meta/bases/{base_id}/tables"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    tables = []
                    for table in data.get("tables", []):
                        fields = [
                            {
                                "id": field["id"],
                                "name": field["name"],
                                "type": field["type"],
                                "description": field.get("description"),
                                "options": field.get("options"),
                            }
                            for field in table.get("fields", [])
                        ]
                        tables.append(
                            {
                                "id": table["id"],
                                "name": table["name"],
                                "description": table.get("description"),
                                "primaryFieldId": table["primaryFieldId"],
                                "fields": fields,
                            }
                        )
                    output_dict = {
                        "tables": tables,
                        "metadata": {
                            "baseId": base_id,
                            "totalTables": len(tables),
                        },
                    }
                    return ToolResult(
                        success=True, output=json.dumps(output_dict), data=output_dict
                    )
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")