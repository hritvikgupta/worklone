from typing import Any, Dict
import httpx
from urllib.parse import quote
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleCalendarDeleteTool(BaseTool):
    name = "google_calendar_delete"
    description = "Delete an event from Google Calendar. Returns API-aligned fields only."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="accessToken",
                description="Access token for Google Calendar API",
                env_var="GOOGLE_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "google",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("GOOGLE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "calendarId": {
                    "type": "string",
                    "description": "Google Calendar ID (e.g., primary or calendar@group.calendar.google.com)",
                },
                "eventId": {
                    "type": "string",
                    "description": "Google Calendar event ID to delete",
                },
                "sendUpdates": {
                    "type": "string",
                    "description": "How to send updates to attendees: all, externalOnly, or none",
                },
            },
            "required": ["eventId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        calendar_id = parameters.get("calendarId", "primary")
        event_id = parameters["eventId"]
        send_updates = parameters.get("sendUpdates")
        
        query_parts = []
        if send_updates is not None:
            query_parts.append(f"sendUpdates={quote(send_updates)}")
        query_string = "&".join(query_parts)
        url = f"https://www.googleapis.com/calendar/v3/calendars/{quote(calendar_id)}/events/{quote(event_id)}{'?' + query_string if query_string else ''}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)
                
                if response.status_code in [200, 204]:
                    return ToolResult(
                        success=True,
                        output="",
                        data={"eventId": event_id, "deleted": True}
                    )
                else:
                    try:
                        error_json = response.json()
                        error_msg = error_json.get("error", {}).get("message", "Failed to delete event")
                    except Exception:
                        error_msg = response.text or f"HTTP {response.status_code}"
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")