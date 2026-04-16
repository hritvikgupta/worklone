from typing import Any, Dict
import httpx
from urllib.parse import quote, urlencode
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleCalendarQuickAddTool(BaseTool):
    name = "google_calendar_quick_add"
    description = "Create events from natural language text. Returns API-aligned fields only."
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

    def _parse_attendees(self, attendees: Any) -> list[str]:
        attendee_list: list[str] = []
        if isinstance(attendees, list):
            attendee_list = [str(email).strip() for email in attendees if str(email).strip()]
        elif isinstance(attendees, str) and attendees.strip():
            attendee_list = [email.strip() for email in attendees.split(",") if email.strip()]
        return attendee_list

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "calendarId": {
                    "type": "string",
                    "description": "Google Calendar ID (e.g., primary or calendar@group.calendar.google.com)",
                },
                "text": {
                    "type": "string",
                    "description": 'Natural language text describing the event (e.g., "Meeting with John tomorrow at 3pm")',
                },
                "attendees": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of attendee email addresses (comma-separated string also accepted)",
                },
                "sendUpdates": {
                    "type": "string",
                    "description": "How to send updates to attendees: all, externalOnly, or none",
                },
            },
            "required": ["text"],
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
        text = parameters["text"]
        query_params = [("text", text)]
        send_updates = parameters.get("sendUpdates")
        if send_updates is not None:
            query_params.append(("sendUpdates", send_updates))
        url = f"https://www.googleapis.com/calendar/v3/calendars/{quote(calendar_id)}/events/quickAdd?{urlencode(query_params)}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers)
                
                if response.status_code not in [200, 201, 204]:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                last_text = response.text
                final_data = data
                
                attendees = parameters.get("attendees")
                if attendees:
                    attendee_list = self._parse_attendees(attendees)
                    if attendee_list:
                        event_id = data["id"]
                        update_data = {
                            "attendees": [{"email": email} for email in attendee_list],
                        }
                        update_query_params: list[tuple[str, str]] = []
                        if send_updates is not None:
                            update_query_params.append(("sendUpdates", send_updates))
                        update_query_str = f"?{urlencode(update_query_params)}" if update_query_params else ""
                        update_url = f"https://www.googleapis.com/calendar/v3/calendars/{quote(calendar_id)}/events/{event_id}{update_query_str}"
                        
                        update_response = await client.patch(update_url, headers=headers, json=update_data)
                        
                        if update_response.status_code in [200, 201, 204]:
                            final_data = update_response.json()
                            last_text = update_response.text
                
                return ToolResult(success=True, output=last_text, data=final_data)
                
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")