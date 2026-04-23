from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class CalcomCreateBookingTool(BaseTool):
    name = "calcom_create_booking"
    description = "Create a new booking on Cal.com"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="CALCOM_ACCESS_TOKEN",
                description="Cal.com OAuth access token",
                env_var="CALCOM_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "calcom",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("CALCOM_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "eventTypeId": {
                    "type": "number",
                    "description": "The ID of the event type to book",
                },
                "start": {
                    "type": "string",
                    "description": "Start time in UTC ISO 8601 format (e.g., 2024-01-15T09:00:00Z)",
                },
                "attendee": {
                    "type": "object",
                    "description": "Attendee information object with name, email, timeZone, and optional phoneNumber (constructed from individual attendee fields)",
                },
                "guests": {
                    "type": "array",
                    "description": "Array of guest email addresses",
                    "items": {
                        "type": "string",
                        "description": "Guest email address",
                    },
                },
                "lengthInMinutes": {
                    "type": "number",
                    "description": "Duration of the booking in minutes (overrides event type default)",
                },
                "metadata": {
                    "type": "object",
                    "description": "Custom metadata to attach to the booking",
                },
            },
            "required": ["eventTypeId", "start", "attendee"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "cal-api-version": "2024-08-13",
        }
        
        url = "https://api.cal.com/v2/bookings"
        
        body = {
            "eventTypeId": parameters["eventTypeId"],
            "start": parameters["start"],
            "attendee": parameters["attendee"],
        }
        
        guests = parameters.get("guests", [])
        if len(guests) > 0:
            body["guests"] = guests
        
        length_in_minutes = parameters.get("lengthInMinutes")
        if length_in_minutes is not None:
            body["lengthInMinutes"] = length_in_minutes
        
        metadata = parameters.get("metadata")
        if metadata is not None:
            body["metadata"] = metadata
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")