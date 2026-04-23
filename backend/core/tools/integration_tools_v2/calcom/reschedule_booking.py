from typing import Any, Dict
import httpx
from urllib.parse import quote
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class CalcomRescheduleBookingTool(BaseTool):
    name = "calcom_reschedule_booking"
    description = "Reschedule an existing booking to a new time"
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
            context_token_keys=("provider_token",),
            env_token_keys=("CALCOM_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "bookingUid": {
                    "type": "string",
                    "description": "Unique identifier (UID) of the booking to reschedule",
                },
                "start": {
                    "type": "string",
                    "description": "New start time in UTC ISO 8601 format (e.g., 2024-01-15T09:00:00Z)",
                },
                "reschedulingReason": {
                    "type": "string",
                    "description": "Reason for rescheduling the booking",
                },
            },
            "required": ["bookingUid", "start"],
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
        
        booking_uid = parameters["bookingUid"]
        url = f"https://api.cal.com/v2/bookings/{quote(booking_uid)}/reschedule"
        
        body = {
            "start": parameters["start"],
        }
        rescheduling_reason = parameters.get("reschedulingReason")
        if rescheduling_reason:
            body["reschedulingReason"] = rescheduling_reason
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")