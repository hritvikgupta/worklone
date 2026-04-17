from typing import Any, Dict
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GreenhouseListJobsTool(BaseTool):
    name = "greenhouse_list_jobs"
    description = "Lists jobs from Greenhouse with optional filtering by status, department, or office"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GREENHOUSE_API_KEY",
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
                "status": {
                    "type": "string",
                    "description": "Filter by job status (open, closed, draft)",
                },
                "created_after": {
                    "type": "string",
                    "description": "Return only jobs created at or after this ISO 8601 timestamp",
                },
                "created_before": {
                    "type": "string",
                    "description": "Return only jobs created before this ISO 8601 timestamp",
                },
                "updated_after": {
                    "type": "string",
                    "description": "Return only jobs updated at or after this ISO 8601 timestamp",
                },
                "updated_before": {
                    "type": "string",
                    "description": "Return only jobs updated before this ISO 8601 timestamp",
                },
                "department_id": {
                    "type": "string",
                    "description": "Filter to jobs in this department ID",
                },
                "office_id": {
                    "type": "string",
                    "description": "Filter to jobs in this office ID",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("GREENHOUSE_API_KEY") if context else None
        
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Basic {base64.b64encode(f'{api_key}:'.encode('utf-8')).decode('utf-8')}",
            "Content-Type": "application/json",
        }
        
        url = "https://harvest.greenhouse.io/v1/jobs"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=parameters)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")