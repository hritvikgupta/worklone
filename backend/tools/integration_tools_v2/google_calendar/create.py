from typing import Any, Dict, List
import httpx
import urllib.parse
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleCalendarCreateTool(BaseTool):
    name = "google_calendar_create"
    description = "Create a new event in Google Calendar. Returns API-aligned fields only."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GOOGLE_CALENDAR_ACCESS_TOKEN",
                description="Access token for Google Calendar API",
                env_var="GOOGLE_CALENDAR_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "google-calendar",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("GOOGLE_CALENDAR_ACCESS_TOKEN",),
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
                "summary": {
                    "type": "string",
                    "description": "Event title/summary",
                },
                "description": {
                    "type": "string",
                    "description": "Event description",
                },
                "location": {
                    "type": "string",
                    "description": "Event location",
                },
                "startDateTime": {
                    "type": "string",
                    "description": "Start date and time. MUST include timezone offset (e.g., 2025-06-03T10:00:00-08:00) OR provide timeZone parameter",
                },
                "endDateTime": {
                    "type": "string",
                    "description": "End date and time. MUST include timezone offset (e.g., 2025-06-03T11:00:00-08:00) OR provide timeZone parameter",
                },
                "timeZone": {
                    "type": "string",
                    "description": "Time zone (e.g., America/Los_Angeles). Required if datetime does not include offset. Defaults to America/Los_Angeles if not provided.",
                    "default": "America/Los_Angeles",
                },
                "attendees": {
                    "type": "array",
                    "items": {
                        "type": "string",
                    },
                    "description": "Array of attendee email addresses",
                },
                "sendUpdates": {
                    "type": "string",
                    "description": "How to send updates to attendees: all, externalOnly, or none",
                },
            },
            "required": ["summary", "startDateTime", "endDateTime"],
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
        url = f"https://www.googleapis.com/calendar/v3/calendars/{urllib.parse.quote(calendar_id)}/events"
        send_updates = parameters.get("sendUpdates")
        if send_updates is not None:
            url += f"?sendUpdates={urllib.parse.quote(str(send_updates))}"
        
        time_zone = parameters.get("timeZone", "America/Los_Angeles")
        start_datetime = parameters["startDateTime"]
        end_datetime = parameters["endDateTime"]
        needs_timezone = "+" not in start_datetime and start_datetime.find("-", 10) == -1
        
        event_data: Dict[str, Any] = {
            "summary": parameters["summary"],
            "start": {
                "dateTime": start_datetime,
            },
            "end": {
                "dateTime": end_datetime,
            },
        }
        
        if needs_timezone:
            event_data["start"]["timeZone"] = time_zone
            event_data["end"]["timeZone"] = time_zone
        
        explicit_time_zone = parameters.get("timeZone")
        if explicit_time_zone:
            event_data["start"]["timeZone"] = explicit_time_zone
            event_data["end"]["timeZone"] = explicit_time_zone
        
        if desc := parameters.get("description"):
            event_data["description"] = desc
        
        if loc := parameters.get("location"):
            event_data["location"] = loc
        
        attendees_param = parameters.get("attendees")
        attendee_list: List[str] = []
        if attendees_param:
            if isinstance(attendees_param, list):
                attendee_list = [email.strip() for email in attendees_param if isinstance(email, str) and email.strip()]
            elif isinstance(attendees_param, str) and attendees_param.strip():
                attendee_list = [email.strip() for email in attendees_param.split(",") if email.strip()]
        
        if attendee_list:
            event_data["attendees"] = [{"email": email} for email in attendee_list]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=event_data)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")