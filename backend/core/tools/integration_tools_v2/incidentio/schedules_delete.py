from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class IncidentioSchedulesDeleteTool(BaseTool):
    name = "incidentio_schedules_delete"
    description = "Delete a schedule in incident.io"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="incidentio_api_key",
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
                "id": {
                    "type": "string",
                    "description": 'The ID of the schedule to delete (e.g., "01FCNDV6P870EA6S7TK1DSYDG0")',
                }
            },
            "required": ["id"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("incidentio_api_key") if context else None
        
        if not api_key or self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="incident.io API key not configured.")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        url = f"https://api.incident.io/v2/schedules/{parameters['id']}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(
                        success=True,
                        output="Schedule deleted successfully",
                        data={"message": "Schedule deleted successfully"},
                    )
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")