from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class VercelRerequestCheckTool(BaseTool):
    name = "vercel_rerequest_check"
    description = "Rerequest a deployment check"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="apiKey",
                description="Vercel Access Token",
                env_var="VERCEL_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "apiKey": {
                    "type": "string",
                    "description": "Vercel Access Token",
                },
                "deploymentId": {
                    "type": "string",
                    "description": "Deployment ID the check belongs to",
                },
                "checkId": {
                    "type": "string",
                    "description": "Check ID to rerequest",
                },
                "teamId": {
                    "type": "string",
                    "description": "Team ID to scope the request",
                },
            },
            "required": ["apiKey", "deploymentId", "checkId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("apiKey") if context else None
        
        if self._is_placeholder_token(api_key or ""):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        deployment_id = (parameters.get("deploymentId") or "").strip()
        check_id = (parameters.get("checkId") or "").strip()
        team_id = (parameters.get("teamId") or "").strip()
        
        if not deployment_id or not check_id:
            return ToolResult(success=False, output="", error="Missing required parameters: deploymentId or checkId.")
        
        url = f"https://api.vercel.com/v1/deployments/{deployment_id}/checks/{check_id}/rerequest"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
        }
        
        params: dict[str, str] = {}
        if team_id:
            params["teamId"] = team_id
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, params=params)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json() if response.text else {})
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")