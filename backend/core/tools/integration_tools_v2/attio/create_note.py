from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class AttioCreateNoteTool(BaseTool):
    name = "attio_create_note"
    description = "Create a note on a record in Attio"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="ATTIO_ACCESS_TOKEN",
                description="The OAuth access token for the Attio API",
                env_var="ATTIO_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "attio",
            context=context,
            context_token_keys=("attio_token",),
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
                    "description": "The parent object type slug (e.g. people, companies)",
                },
                "parentRecordId": {
                    "type": "string",
                    "description": "The parent record ID to attach the note to",
                },
                "title": {
                    "type": "string",
                    "description": "The note title",
                },
                "content": {
                    "type": "string",
                    "description": "The note content",
                },
                "format": {
                    "type": "string",
                    "description": "Content format: plaintext or markdown (default plaintext)",
                },
                "createdAt": {
                    "type": "string",
                    "description": "Backdate the note creation time (ISO 8601 format)",
                },
                "meetingId": {
                    "type": "string",
                    "description": "Associate the note with a meeting ID",
                },
            },
            "required": ["parentObject", "parentRecordId", "title", "content"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = "https://api.attio.com/v2/notes"
        
        body = {
            "data": {
                "parent_object": parameters["parentObject"],
                "parent_record_id": parameters["parentRecordId"],
                "title": parameters["title"],
                "format": parameters.get("format", "plaintext"),
                "content": parameters["content"],
            }
        }
        created_at = parameters.get("createdAt")
        if created_at:
            body["data"]["created_at"] = created_at
        meeting_id = parameters.get("meetingId")
        if meeting_id is not None:
            body["data"]["meeting_id"] = meeting_id
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")