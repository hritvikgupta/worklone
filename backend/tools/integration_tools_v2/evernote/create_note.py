from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class EvernoteCreateNoteTool(BaseTool):
    name = "evernote_create_note"
    description = "Create a new note in Evernote"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="apiKey",
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
                "title": {
                    "type": "string",
                    "description": "Title of the note",
                },
                "content": {
                    "type": "string",
                    "description": "Content of the note (plain text or ENML)",
                },
                "notebookGuid": {
                    "type": "string",
                    "description": "GUID of the notebook to create the note in (defaults to default notebook)",
                },
                "tagNames": {
                    "type": "string",
                    "description": "Comma-separated list of tag names to apply",
                },
            },
            "required": ["title", "content"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        title = parameters.get("title")
        content = parameters.get("content")
        
        if not title or not content:
            return ToolResult(success=False, output="", error="title and content are required")
        
        notebook_guid = parameters.get("notebookGuid")
        tag_names_str = parameters.get("tagNames")
        
        parsed_tags = None
        if tag_names_str:
            tags = []
            for t in str(tag_names_str).split(","):
                trimmed = t.strip()
                if trimmed:
                    tags.append(trimmed)
            if tags:
                parsed_tags = tags
        
        body = {
            "title": title,
            "content": content,
        }
        if notebook_guid is not None:
            body["notebookGuid"] = notebook_guid
        if parsed_tags is not None:
            body["tagNames"] = parsed_tags
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = "https://www.evernote.com/edam/notestore"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    return ToolResult(success=True, output=response.text, data={"note": data})
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")