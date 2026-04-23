from typing import Any, Dict
import httpx
from urllib.parse import quote
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class CalcomUpdateScheduleTool(BaseTool):
    name = "calcom_update_schedule"
    description = "Update an existing schedule in Cal.com"
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
            context_token_keys=("calcom_token",),
            env_token_keys=("CALCOM_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "scheduleId": {
                    "type": "string",
                    "description": "ID of the schedule to update",
                },
                "name": {
                    "type": "string",
                    "description": "New name for the schedule",
                },
                "timeZone": {
                    "type": "string",
                    "description": "New timezone for the schedule (e.g., America/New_York)",
                },
                "isDefault": {
                    "type": "boolean",
                    "description": "Whether this schedule should be the default",
                },
                "availability": {
                    "type": "array",
                    "description": "New availability intervals for the schedule",
                    "items": {
                        "type": "object",
                        "description": "Availability interval",
                        "properties": {
                            "days": {
                                "type": "array",
                                "description": "Days of the week (Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday)",
                                "items": {"type": "string"},
                            },
                            "startTime": {
                                "type": "string",
                                "description": "Start time in HH:MM format",
                            },
                            "endTime": {
                                "type": "string",
                                "description": "End time in HH:MM format",
                            },
                        },
                    },
                },
            },
            "required": ["scheduleId"],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        url = f"https://api.cal.com/v2/schedules/{quote(parameters['scheduleId'])}"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "cal-api-version": "2024-06-11",
        }
        
        body: Dict[str, Any] = {}
        for field in ["name", "timeZone", "isDefault", "availability"]:
            if field in parameters:
                body[field] = parameters[field]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")