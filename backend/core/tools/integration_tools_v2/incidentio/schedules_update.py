from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class IncidentioSchedulesUpdateTool(BaseTool):
    name = "incidentio_schedules_update"
    description = "Update an existing schedule in incident.io"
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

    async def _resolve_access_token(self, context: dict | None) -> str:
        return (context.get("apiKey") if context else None) or ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "description": 'The ID of the schedule to update (e.g., "01FCNDV6P870EA6S7TK1DSYDG0")',
                },
                "name": {
                    "type": "string",
                    "description": 'New name for the schedule (e.g., "Primary On-Call")',
                },
                "timezone": {
                    "type": "string",
                    "description": 'New timezone for the schedule (e.g., America/New_York)',
                },
                "config": {
                    "type": "string",
                    "description": 'Schedule configuration as JSON string with rotations. Example: {"rotations": [{"name": "Primary", "users": [{"id": "user_id"}], "handover_start_at": "2024-01-01T09:00:00Z", "handovers": [{"interval": 1, "interval_type": "weekly"}]}]}',
                },
            },
            "required": ["id"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        id_ = parameters.get("id")
        if not id_:
            return ToolResult(success=False, output="", error="Missing required parameter: id")

        url = f"https://api.incident.io/v2/schedules/{id_}"

        schedule_dict: Dict[str, Any] = {}
        if name := parameters.get("name"):
            schedule_dict["name"] = name
        if timezone := parameters.get("timezone"):
            schedule_dict["timezone"] = timezone
        if config := parameters.get("config"):
            try:
                schedule_dict["config"] = json.loads(config) if isinstance(config, str) else config
            except json.JSONDecodeError:
                return ToolResult(success=False, output="", error="Invalid JSON in config parameter")

        body = {"schedule": schedule_dict}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.put(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")