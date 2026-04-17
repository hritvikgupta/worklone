from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class AttioListNotesTool(BaseTool):
    name = "attio_list_notes"
    description = "List notes in Attio, optionally filtered by parent record"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="ATTIO_ACCESS_TOKEN",
                description="OAuth access token for the Attio API",
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
                "parentObject": {
                    "type": "string",
                    "description": "Object type slug to filter notes by (e.g. people, companies)",
                },
                "parentRecordId": {
                    "type": "string",
                    "description": "Record ID to filter notes by",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of notes to return (default 10, max 50)",
                },
                "offset": {
                    "type": "number",
                    "description": "Number of notes to skip for pagination",
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
        }
        
        url = "https://api.attio.com/v2/notes"
        params_dict: Dict[str, Any] = {}
        if parameters.get("parentObject"):
            params_dict["parent_object"] = parameters["parentObject"]
        if parameters.get("parentRecordId"):
            params_dict["parent_record_id"] = parameters["parentRecordId"]
        if parameters.get("limit") is not None:
            params_dict["limit"] = parameters["limit"]
        if parameters.get("offset") is not None:
            params_dict["offset"] = parameters["offset"]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params_dict)
                
                if response.status_code == 200:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")