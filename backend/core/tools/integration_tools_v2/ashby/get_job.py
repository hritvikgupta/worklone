from typing import Any, Dict
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class AshbyGetJobTool(BaseTool):
    name = "ashby_get_job"
    description = "Retrieves full details about a single job by its ID."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="ASHBY_API_KEY",
                description="Ashby API Key",
                env_var="ASHBY_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def _resolve_api_key(self, context: dict | None) -> str:
        return (context.get("provider_token") if context else "")

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "jobId": {
                    "type": "string",
                    "description": "The UUID of the job to fetch",
                },
            },
            "required": ["jobId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = self._resolve_api_key(context)
        
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Basic {base64.b64encode(f'{api_key}:'.encode('utf-8')).decode('utf-8')}",
            "Content-Type": "application/json",
        }
        
        url = "https://api.ashbyhq.com/job.info"
        body = {
            "jobId": (parameters.get("jobId") or "").strip(),
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    try:
                        data = response.json()
                    except Exception:
                        return ToolResult(success=False, output="", error="Invalid JSON response")
                    
                    if not data.get("success"):
                        error_msg = "Failed to get job"
                        error_info = data.get("errorInfo")
                        if isinstance(error_info, dict) and "message" in error_info:
                            error_msg = error_info["message"]
                        return ToolResult(success=False, output="", error=error_msg)
                    
                    return ToolResult(success=True, output=response.text, data=data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")