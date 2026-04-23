from typing import Any, Dict
import httpx
import json
import os
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class IncidentioSchedulesCreateTool(BaseTool):
    name = "incidentio_schedules_create"
    description = "Create a new schedule in incident.io"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="api_key",
                description="incident.io API Key",
                env_var="INCIDENTIO_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_api_key(self, context: dict | None) -> str:
        api_key = context.get("api_key") if context else None
        if not api_key:
            api_key = os.getenv("INCIDENTIO_API_KEY")
        return api_key

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": 'Name of the schedule (e.g., "Primary On-Call")',
                },
                "timezone": {
                    "type": "string",
                    "description": 'Timezone for the schedule (e.g., America/New_York)',
                },
                "config": {
                    "type": "string",
                    "description": """Schedule configuration as JSON string with rotations. Example: {"rotations": [{"name": "Primary", "users": [{"id": "user_id"}], "handover_start_at": "2024-01-01T09:00:00Z", "handovers": [{"interval": 1, "interval_type": "weekly"}]}]}""",
                },
            },
            "required": ["name", "timezone", "config"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = await self._resolve_api_key(context)
        
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="API key not configured.")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        try:
            config_obj = json.loads(parameters["config"])
            body = {
                "schedule": {
                    "name": parameters["name"],
                    "timezone": parameters["timezone"],
                    "config": config_obj,
                }
            }
            url = "https://api.incident.io/v2/schedules"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except json.JSONDecodeError as e:
            return ToolResult(success=False, output="", error=f"Invalid config JSON: {str(e)}")
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")