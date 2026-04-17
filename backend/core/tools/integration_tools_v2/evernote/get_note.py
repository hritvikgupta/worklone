from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class EvernoteGetNoteTool(BaseTool):
    name = "evernote_get_note"
    description = "Retrieve a note from Evernote by its GUID"
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

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "apiKey": {
                    "type": "string",
                    "description": "Evernote developer token",
                },
                "noteGuid": {
                    "type": "string",
                    "description": "GUID of the note to retrieve",
                },
                "withContent": {
                    "type": "boolean",
                    "description": "Whether to include note content (default: true)",
                },
            },
            "required": ["apiKey", "noteGuid"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = parameters.get("apiKey")
        note_guid = parameters.get("noteGuid")
        with_content = parameters.get("withContent", True)

        if not api_key or not note_guid:
            return ToolResult(success=False, output="", error="apiKey and noteGuid are required")

        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Evernote developer token not configured.")

        headers = {
            "Authorization": f"DeveloperToken {api_key}",
            "Accept": "application/json",
        }

        shard_id = "s29"
        url = f"https://app.evernote.com/shard/{shard_id}/edam/note/{note_guid}?withContent={with_content}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code in [200]:
                    return ToolResult(success=True, output=response.text, data={"note": response.json()})
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")