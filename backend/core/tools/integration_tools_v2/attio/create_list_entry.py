from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class AttioCreateListEntryTool(BaseTool):
    name = "attio_create_list_entry"
    description = "Add a record to an Attio list as a new entry"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="ATTIO_ACCESS_TOKEN",
                description="Attio access token",
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
                "list": {
                    "type": "string",
                    "description": "The list ID or slug",
                },
                "parentRecordId": {
                    "type": "string",
                    "description": "The record ID to add to the list",
                },
                "parentObject": {
                    "type": "string",
                    "description": "The object type slug of the record (e.g. people, companies)",
                },
                "entryValues": {
                    "type": "string",
                    "description": "JSON object of entry attribute values",
                },
            },
            "required": ["list", "parentRecordId", "parentObject"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        list_id = parameters["list"].strip()
        url = f"https://api.attio.com/v2/lists/{list_id}/entries"
        
        entry_values: dict = {}
        entry_values_param = parameters.get("entryValues")
        if entry_values_param:
            try:
                entry_values = json.loads(entry_values_param)
            except (json.JSONDecodeError, ValueError, TypeError):
                pass
        
        body = {
            "data": {
                "parent_record_id": parameters["parentRecordId"],
                "parent_object": parameters["parentObject"],
                "entry_values": entry_values,
            }
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