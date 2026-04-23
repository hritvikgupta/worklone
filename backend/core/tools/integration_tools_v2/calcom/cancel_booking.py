from typing import Any, Dict
import httpx
import urllib.parse
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class CalcomCancelBookingTool(BaseTool):
    name = "calcom_cancel_booking"
    description = "Cancel an existing booking"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="CALCOM_ACCESS_TOKEN",
                description="Access token",
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
                    "description": "Unique identifier (UID) of the booking to cancel",
                },
                "cancellationReason": {
                    "type": "string",
                    "description": "Reason for cancelling the booking",
                },
            },
            "required": ["bookingUid"],
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
        
        url = f"https://api.cal.com/v2/bookings/{urllib.parse.quote(parameters['bookingUid'])}/cancel"
        
        body: Dict[str, Any] = {}
        if parameters.get("cancellationReason"):
            body["cancellationReason"] = parameters["cancellationReason"]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")