from typing import Any, Dict
import httpx
import base64
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GreenhouseGetJobTool(BaseTool):
    name = "greenhouse_get_job"
    description = "Retrieves a specific job by ID with full details including hiring team, openings, and custom fields"
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

    async def _resolve_api_key(self, context: dict | None) -> str:
        if context is None:
            return ""
        return context.get("GREENHOUSE_API_KEY", "")

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "jobId": {
                    "type": "string",
                    "description": "The ID of the job to retrieve",
                },
            },
            "required": ["jobId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = await self._resolve_api_key(context)
        
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Greenhouse API key not configured.")
        
        headers = {
            "Authorization": f"Basic {base64.b64encode(f'{api_key}:'.encode('utf-8')).decode('utf-8')}",
            "Content-Type": "application/json",
        }
        
        job_id = parameters["jobId"].strip()
        url = f"https://harvest.greenhouse.io/v1/jobs/{job_id}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")