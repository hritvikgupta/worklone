from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleCalendarListCalendarsTool(BaseTool):
    name = "google_calendar_list_calendars"
    description = "List all calendars in the user's calendar list. Returns API-aligned fields only."
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
                "minAccessRole": {
                    "type": "string",
                    "description": "Minimum access role for returned calendars: freeBusyReader, reader, writer, or owner",
                    "enum": ["freeBusyReader", "reader", "writer", "owner"]
                },
                "maxResults": {
                    "type": "number",
                    "description": "Maximum number of calendars to return (default 100, max 250)"
                },
                "pageToken": {
                    "type": "string",
                    "description": "Token for retrieving subsequent pages of results"
                },
                "showDeleted": {
                    "type": "boolean",
                    "description": "Include deleted calendars"
                },
                "showHidden": {
                    "type": "boolean",
                    "description": "Include hidden calendars"
                }
            },
            "required": []
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = "https://www.googleapis.com/calendar/v3/users/me/calendarList"
        query_params = {}
        for key in ["minAccessRole", "maxResults", "pageToken", "showDeleted", "showHidden"]:
            if key in parameters:
                query_params[key] = parameters[key]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)
                
                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    calendars = data.get("items", [])
                    calendars_list = []
                    for calendar in calendars:
                        calendars_list.append({
                            "id": calendar["id"],
                            "summary": calendar.get("summaryOverride") or calendar["summary"],
                            "description": calendar.get("description"),
                            "location": calendar.get("location"),
                            "timeZone": calendar["timeZone"],
                            "accessRole": calendar["accessRole"],
                            "backgroundColor": calendar["backgroundColor"],
                            "foregroundColor": calendar["foregroundColor"],
                            "primary": calendar.get("primary"),
                            "hidden": calendar.get("hidden"),
                            "selected": calendar.get("selected"),
                        })
                    output_data = {
                        "nextPageToken": data.get("nextPageToken"),
                        "calendars": calendars_list
                    }
                    return ToolResult(success=True, output=json.dumps(output_data), data=output_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")