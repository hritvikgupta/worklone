from typing import Any, Dict, List
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection

class EvernoteUpdateNoteTool(BaseTool):
    name = "evernote_update_note"
    description = "Update an existing note in Evernote"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> List[CredentialRequirement]:
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
                "noteGuid": {
                    "type": "string",
                    "description": "GUID of the note to update",
                },
                "title": {
                    "type": "string",
                    "description": "New title for the note",
                },
                "content": {
                    "type": "string",
                    "description": "New content for the note (plain text or ENML)",
                },
                "notebookGuid": {
                    "type": "string",
                    "description": "GUID of the notebook to move the note to",
                },
                "tagNames": {
                    "type": "string",
                    "description": "Comma-separated list of tag names (replaces existing tags)",
                },
            },
            "required": ["noteGuid"],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "User-Agent": "BackendAgent/1.0",
            "X-Evernote-Auth": f"token={access_token}",
            "Content-Type": "application/json",
        }

        note_guid = parameters["noteGuid"]
        title = parameters.get("title")
        content = parameters.get("content")
        notebook_guid = parameters.get("notebookGuid")
        tag_names = parameters.get("tagNames")

        parsed_tags = None
        if tag_names:
            tags = []
            if isinstance(tag_names, str):
                tags = [t.strip() for t in tag_names.split(",") if t.strip()]
            elif isinstance(tag_names, list):
                tags = [str(t).strip() for t in tag_names if t and str(t).strip()]
            if tags:
                parsed_tags = tags

        body = {
            "noteGuid": note_guid,
            "title": title,
            "content": content,
            "notebookGuid": notebook_guid,
            "tagNames": parsed_tags,
        }

        url = "https://www.evernote.com/edam/note/NoteStore"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    data = response.json() if response.text else {}
                    return ToolResult(
                        success=True,
                        output=response.text,
                        data={"note": data.get("note", data) if isinstance(data, dict) else data},
                    )
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")