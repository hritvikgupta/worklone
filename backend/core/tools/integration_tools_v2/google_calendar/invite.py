from typing import Any, Dict
import httpx
import json
import urllib.parse
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleCalendarInviteTool(BaseTool):
    name = "google_calendar_invite"
    description = "Invite attendees to an existing Google Calendar event. Returns API-aligned fields only."
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
            context_token_keys=("google_token",),
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
                    "description": "Google Calendar event ID to invite attendees to",
                },
                "attendees": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of attendee email addresses to invite",
                },
                "sendUpdates": {
                    "type": "string",
                    "description": "How to send updates to attendees: all, externalOnly, or none",
                },
                "replaceExisting": {
                    "type": "boolean",
                    "description": "Whether to replace existing attendees or add to them (defaults to false)",
                },
            },
            "required": ["eventId", "attendees"],
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
        get_url = f"https://www.googleapis.com/calendar/v3/calendars/{urllib.parse.quote(calendar_id)}/events/{urllib.parse.quote(event_id)}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                get_response = await client.get(get_url, headers=headers)

                if get_response.status_code != 200:
                    try:
                        error_data = get_response.json()
                        error_msg = error_data.get("error", {}).get("message", get_response.text)
                    except Exception:
                        error_msg = get_response.text
                    return ToolResult(success=False, output="", error=error_msg or "Failed to fetch event")

                existing_event = get_response.json()

                if not all(key in existing_event for key in ["start", "end", "summary"]):
                    return ToolResult(
                        success=False,
                        output="",
                        error="Existing event is missing required fields (start, end, or summary)",
                    )

                attendees_param = parameters.get("attendees", [])
                new_attendee_list = []
                if isinstance(attendees_param, list):
                    new_attendee_list = [e.strip() for e in attendees_param if e and e.strip()]
                elif isinstance(attendees_param, str) and attendees_param.strip():
                    new_attendee_list = [e.strip() for e in attendees_param.split(",") if e.strip()]

                existing_attendees = existing_event.get("attendees", [])
                should_replace = bool(parameters.get("replaceExisting", False))
                final_attendees = []
                if should_replace:
                    final_attendees = [
                        {"email": email, "responseStatus": "needsAction"}
                        for email in new_attendee_list
                    ]
                else:
                    final_attendees = list(existing_attendees)
                    existing_emails = {a.get("email", "").lower() for a in existing_attendees}
                    for email in new_attendee_list:
                        email_lower = email.lower()
                        if email_lower not in existing_emails:
                            final_attendees.append({"email": email, "responseStatus": "needsAction"})
                            existing_emails.add(email_lower)

                updated_event = {**existing_event, "attendees": final_attendees}
                read_only_fields = [
                    "id",
                    "etag",
                    "kind",
                    "created",
                    "updated",
                    "htmlLink",
                    "iCalUID",
                    "sequence",
                    "creator",
                    "organizer",
                ]
                for field in read_only_fields:
                    updated_event.pop(field, None)

                query_params = []
                send_updates = parameters.get("sendUpdates")
                if send_updates is not None:
                    query_params.append(f"sendUpdates={urllib.parse.quote(str(send_updates))}")
                query_string = "&".join(query_params)
                put_url = f"https://www.googleapis.com/calendar/v3/calendars/{urllib.parse.quote(calendar_id)}/events/{urllib.parse.quote(event_id)}"
                if query_string:
                    put_url += f"?{query_string}"

                put_response = await client.put(put_url, headers=headers, json=updated_event)

                if put_response.status_code not in [200, 201, 204]:
                    try:
                        error_data = put_response.json()
                        error_msg = error_data.get("error", {}).get("message", put_response.text)
                    except Exception:
                        error_msg = put_response.text
                    return ToolResult(success=False, output="", error=error_msg or "Failed to invite attendees to calendar event")

                data = put_response.json()

                output_dict = {
                    "id": data["id"],
                    "htmlLink": data.get("htmlLink"),
                    "status": data.get("status"),
                    "summary": data.get("summary"),
                    "description": data.get("description"),
                    "location": data.get("location"),
                    "start": data["start"],
                    "end": data["end"],
                    "attendees": data.get("attendees"),
                    "creator": data["creator"],
                    "organizer": data["organizer"],
                }

                return ToolResult(
                    success=True,
                    output=json.dumps(output_dict),
                    data=output_dict,
                )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")