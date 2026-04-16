from typing import Any, Dict
import httpx
import urllib.parse
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleCalendarMoveTool(BaseTool):
    name = "google_calendar_move"
    description = "Move an event to a different calendar. Returns API-aligned fields only."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GOOGLE_ACCESS_TOKEN",
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
                    "description": "Source Google Calendar ID (e.g., primary or calendar@group.calendar.google.com)",
                },
                "eventId": {
                    "type": "string",
                    "description": "Google Calendar event ID to move",
                },
                "destinationCalendarId": {
                    "type": "string",
                    "description": "Destination Google Calendar ID",
                },
                "sendUpdates": {
                    "type": "string",
                    "description": "How to send updates to attendees: all, externalOnly, or none",
                },
            },
            "required": ["eventId", "destinationCalendarId"],
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
        destination_calendar_id = parameters["destinationCalendarId"]
        send_updates = parameters.get("sendUpdates")
        
        query_params = {
            "destination": destination_calendar_id,
        }
        if send_updates is not None:
            query_params["sendUpdates"] = send_updates
        
        url = f"https://www.googleapis.com/calendar/v3/calendars/{urllib.parse.quote(calendar_id)}/events/{urllib.parse.quote(event_id)}/move"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, params=query_params, json={})
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")