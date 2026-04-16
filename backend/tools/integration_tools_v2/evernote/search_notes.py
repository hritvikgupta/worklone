from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class EvernoteSearchNotesTool(BaseTool):
    name = "evernote_search_notes"
    description = "Search for notes in Evernote using the Evernote search grammar"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="EVERNOTE_DEVELOPER_TOKEN",
                description="Evernote developer token",
                env_var="EVERNOTE_DEVELOPER_TOKEN",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "evernote",
            context=context,
            context_token_keys=("apiKey",),
            env_token_keys=("EVERNOTE_DEVELOPER_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query using Evernote search grammar (e.g., \"tag:work intitle:meeting\")",
                },
                "notebookGuid": {
                    "type": "string",
                    "description": "Restrict search to a specific notebook by GUID",
                },
                "offset": {
                    "type": "number",
                    "description": "Starting index for results (default: 0)",
                },
                "maxNotes": {
                    "type": "number",
                    "description": "Maximum number of notes to return (default: 25)",
                },
            },
            "required": ["query"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        query = parameters.get("query")
        if not query:
            return ToolResult(success=False, output="", error="query is required")
        
        offset = int(parameters.get("offset", 0))
        max_notes_input = parameters.get("maxNotes")
        max_notes = int(max_notes_input) if max_notes_input is not None else 25
        clamped_max_notes = min(max(max_notes, 1), 250)
        notebook_guid = parameters.get("notebookGuid")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        json_body = {
            "query": query,
            "notebookGuid": notebook_guid or None,
            "offset": offset,
            "maxNotes": clamped_max_notes,
        }
        
        url = "https://sandbox.evernote.com/edam/note"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=json_body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")