from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class IncidentioScheduleOverridesCreateTool(BaseTool):
    name = "incidentio_schedule_overrides_create"
    description = "Create a new schedule override in incident.io"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="apiKey",
                description="incident.io API Key",
                env_var="INCIDENTIO_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "rotation_id": {
                    "type": "string",
                    "description": "The ID of the rotation to override (e.g., \"01FCNDV6P870EA6S7TK1DSYDG0\")",
                },
                "schedule_id": {
                    "type": "string",
                    "description": "The ID of the schedule (e.g., \"01FCNDV6P870EA6S7TK1DSYDG0\")",
                },
                "user_id": {
                    "type": "string",
                    "description": "The ID of the user to assign (provide one of: user_id, user_email, or user_slack_id)",
                },
                "user_email": {
                    "type": "string",
                    "description": "The email of the user to assign (provide one of: user_id, user_email, or user_slack_id)",
                },
                "user_slack_id": {
                    "type": "string",
                    "description": "The Slack ID of the user to assign (provide one of: user_id, user_email, or user_slack_id)",
                },
                "start_at": {
                    "type": "string",
                    "description": "When the override starts in ISO 8601 format (e.g., \"2024-01-15T09:00:00Z\")",
                },
                "end_at": {
                    "type": "string",
                    "description": "When the override ends in ISO 8601 format (e.g., \"2024-01-22T09:00:00Z\")",
                },
            },
            "required": ["rotation_id", "schedule_id", "start_at", "end_at"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("apiKey") if context else None
        if not api_key or self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="incident.io API key not configured.")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        user: dict = {}
        if parameters.get("user_id"):
            user["id"] = parameters["user_id"]
        if parameters.get("user_email"):
            user["email"] = parameters["user_email"]
        if parameters.get("user_slack_id"):
            user["slack_user_id"] = parameters["user_slack_id"]

        body = {
            "rotation_id": parameters["rotation_id"],
            "schedule_id": parameters["schedule_id"],
            "user": user,
            "start_at": parameters["start_at"],
            "end_at": parameters["end_at"],
        }

        url = "https://api.incident.io/v2/schedule_overrides"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")