from typing import Any, Dict
import httpx
import base64
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GreenhouseListApplicationsTool(BaseTool):
    name = "greenhouse_list_applications"
    description = "Lists applications from Greenhouse with optional filtering by job, status, or date"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="api_key",
                description="Greenhouse Harvest API key",
                env_var="GREENHOUSE_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "per_page": {
                    "type": "number",
                    "description": "Number of results per page (1-500, default 100)",
                },
                "page": {
                    "type": "number",
                    "description": "Page number for pagination",
                },
                "job_id": {
                    "type": "string",
                    "description": "Filter applications by job ID",
                },
                "status": {
                    "type": "string",
                    "description": "Filter by status (active, converted, hired, rejected)",
                },
                "created_after": {
                    "type": "string",
                    "description": "Return only applications created at or after this ISO 8601 timestamp",
                },
                "created_before": {
                    "type": "string",
                    "description": "Return only applications created before this ISO 8601 timestamp",
                },
                "last_activity_after": {
                    "type": "string",
                    "description": "Return only applications with activity at or after this ISO 8601 timestamp",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("api_key") if context else None
        
        if not api_key or self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="API key not configured.")
        
        headers = {
            "Authorization": f"Basic {base64.b64encode(f'{api_key}:'.encode('utf-8')).decode('utf-8')}",
            "Content-Type": "application/json",
        }
        
        url = "https://harvest.greenhouse.io/v1/applications"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=parameters)
                
                if response.status_code == 200:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")