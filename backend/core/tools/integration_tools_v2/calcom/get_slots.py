from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class CalcomGetSlotsTool(BaseTool):
    name = "calcom_get_slots"
    description = "Get available booking slots for a Cal.com event type within a time range"
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
                "start": {
                    "type": "string",
                    "description": "Start of time range in UTC ISO 8601 format (e.g., 2024-01-15T00:00:00Z)",
                },
                "end": {
                    "type": "string",
                    "description": "End of time range in UTC ISO 8601 format (e.g., 2024-01-22T00:00:00Z)",
                },
                "eventTypeId": {
                    "type": "number",
                    "description": "Event type ID for direct lookup",
                },
                "eventTypeSlug": {
                    "type": "string",
                    "description": "Event type slug (requires username to be set)",
                },
                "username": {
                    "type": "string",
                    "description": "Username for personal event types (required when using eventTypeSlug)",
                },
                "timeZone": {
                    "type": "string",
                    "description": "Timezone for returned slots (defaults to UTC)",
                },
                "duration": {
                    "type": "number",
                    "description": "Slot length in minutes",
                },
            },
            "required": ["start", "end"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "cal-api-version": "2024-09-04",
        }
        
        query_params = {
            "start": parameters["start"],
            "end": parameters["end"],
        }
        for key in ["eventTypeId", "eventTypeSlug", "username", "timeZone", "duration"]:
            if key in parameters:
                value = parameters[key]
                if value is not None and str(value).strip() != "":
                    query_params[key] = value
        
        url = "https://api.cal.com/v2/slots"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")