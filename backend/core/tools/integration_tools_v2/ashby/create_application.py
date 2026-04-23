from typing import Any, Dict
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class AshbyCreateApplicationTool(BaseTool):
    name = "ashby_create_application"
    description = "Creates a new application for a candidate on a job. Optionally specify interview plan, stage, source, and credited user."
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
        return (context or {}).get("ASHBY_API_KEY", "")

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "candidateId": {
                    "type": "string",
                    "description": "The UUID of the candidate to consider for the job",
                },
                "jobId": {
                    "type": "string",
                    "description": "The UUID of the job to consider the candidate for",
                },
                "interviewPlanId": {
                    "type": "string",
                    "description": "UUID of the interview plan to use (defaults to the job default plan)",
                },
                "interviewStageId": {
                    "type": "string",
                    "description": "UUID of the interview stage to place the application in (defaults to first Lead stage)",
                },
                "sourceId": {
                    "type": "string",
                    "description": "UUID of the source to set on the application",
                },
                "creditedToUserId": {
                    "type": "string",
                    "description": "UUID of the user the application is credited to",
                },
                "createdAt": {
                    "type": "string",
                    "description": "ISO 8601 timestamp to set as the application creation date (defaults to now)",
                },
            },
            "required": ["candidateId", "jobId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = self._resolve_api_key(context)
        
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Ashby API key not configured.")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {base64.b64encode(f'{api_key}:'.encode('utf-8')).decode('utf-8')}",
        }
        
        url = "https://api.ashbyhq.com/application.create"
        
        body = {
            "candidateId": parameters["candidateId"],
            "jobId": parameters["jobId"],
        }
        for field in ["interviewPlanId", "interviewStageId", "sourceId", "creditedToUserId", "createdAt"]:
            if field in parameters:
                body[field] = parameters[field]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")