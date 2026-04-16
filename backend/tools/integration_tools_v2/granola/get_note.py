from typing import Any, Dict
import httpx
import json
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GranolaGetNoteTool(BaseTool):
    name = "granola_get_note"
    description = "Retrieves a specific meeting note from Granola by ID, including summary, attendees, calendar event details, and optionally the transcript."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GRANOLA_API_KEY",
                description="Granola API key",
                env_var="GRANOLA_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "granola",
            context=context,
            context_token_keys=("GRANOLA_API_KEY",),
            env_token_keys=("GRANOLA_API_KEY",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def _transform_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        calendar_event = data.get("calendar_event", {})
        owner = data.get("owner", {})
        raw_transcript = data.get("transcript")
        transcript = None
        if raw_transcript:
            transcript = [
                {
                    "speaker": t.get("speaker", {}).get("source", "unknown"),
                    "text": t.get("text", ""),
                    "startTime": t.get("start_time", ""),
                    "endTime": t.get("end_time", ""),
                }
                for t in raw_transcript
            ]
        return {
            "id": data.get("id", ""),
            "title": data.get("title"),
            "ownerName": owner.get("name"),
            "ownerEmail": owner.get("email", ""),
            "createdAt": data.get("created_at", ""),
            "updatedAt": data.get("updated_at", ""),
            "summaryText": data.get("summary_text", ""),
            "summaryMarkdown": data.get("summary_markdown"),
            "attendees": [
                {
                    "name": a.get("name"),
                    "email": a.get("email", ""),
                }
                for a in data.get("attendees", [])
            ],
            "folders": [
                {
                    "id": f.get("id", ""),
                    "name": f.get("name", ""),
                }
                for f in data.get("folder_membership", [])
            ],
            "calendarEventTitle": calendar_event.get("event_title"),
            "calendarOrganiser": calendar_event.get("organiser"),
            "calendarEventId": calendar_event.get("calendar_event_id"),
            "scheduledStartTime": calendar_event.get("scheduled_start_time"),
            "scheduledEndTime": calendar_event.get("scheduled_end_time"),
            "invitees": [i.get("email", "") for i in calendar_event.get("invitees", [])],
            "transcript": transcript,
        }

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "noteId": {
                    "type": "string",
                    "description": "The note ID (e.g., not_1d3tmYTlCICgjy)",
                },
                "includeTranscript": {
                    "type": "string",
                    "description": "Whether to include the meeting transcript",
                },
            },
            "required": ["noteId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        note_id = parameters["noteId"].strip()
        url = f"https://public-api.granola.ai/v1/notes/{note_id}"
        if parameters.get("includeTranscript") == "true":
            url += "?include=transcript"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    response_data = response.json()
                    transformed = self._transform_response(response_data)
                    return ToolResult(success=True, output=json.dumps(transformed), data=transformed)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")