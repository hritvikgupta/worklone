from typing import Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class IncidentioEscalationsListTool(BaseTool):
    name = "incidentio_escalations_list"
    description = "List all escalation policies in incident.io"
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
            "properties": {},
            "required": []
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("apiKey") if context else None
        
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="API key not configured.")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        url = "https://api.incident.io/v2/escalations"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")