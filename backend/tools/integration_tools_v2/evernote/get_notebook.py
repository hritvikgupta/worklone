from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class EvernoteGetNotebookTool(BaseTool):
    name = "evernote_get_notebook"
    description = "Retrieve a notebook from Evernote by its GUID"
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
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "apiKey": {
                    "type": "string",
                    "description": "Evernote developer token",
                },
                "notebookGuid": {
                    "type": "string",
                    "description": "GUID of the notebook to retrieve",
                },
            },
            "required": ["apiKey", "notebookGuid"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        notebook_guid = parameters.get("notebookGuid")
        if not notebook_guid:
            return ToolResult(success=False, output="", error="notebookGuid is required.")
        
        host = "sandbox.evernote.com" if access_token.startswith("S") else "www.evernote.com"
        url = f"https://{host}/edam/NoteStore"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url, 
                    headers=headers, 
                    json={"guid": notebook_guid}
                )
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")