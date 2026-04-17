from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class VercelCreateCheckTool(BaseTool):
    name = "Vercel Create Check"
    description = "Create a new deployment check"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="VERCEL_ACCESS_TOKEN",
                description="Vercel Access Token",
                env_var="VERCEL_ACCESS_TOKEN",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        token = (context or {}).get("VERCEL_ACCESS_TOKEN", "")
        return token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "deploymentId": {
                    "type": "string",
                    "description": "Deployment ID to create the check for",
                },
                "name": {
                    "type": "string",
                    "description": "Name of the check (max 100 characters)",
                },
                "blocking": {
                    "type": "boolean",
                    "description": "Whether the check blocks the deployment",
                },
                "path": {
                    "type": "string",
                    "description": "Page path being checked",
                },
                "detailsUrl": {
                    "type": "string",
                    "description": "URL with details about the check",
                },
                "externalId": {
                    "type": "string",
                    "description": "External identifier for the check",
                },
                "rerequestable": {
                    "type": "boolean",
                    "description": "Whether the check can be rerequested",
                },
                "teamId": {
                    "type": "string",
                    "description": "Team ID to scope the request",
                },
            },
            "required": ["deploymentId", "name", "blocking"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        deployment_id = parameters["deploymentId"].strip()
        url = f"https://api.vercel.com/v1/deployments/{deployment_id}/checks"
        
        team_id = parameters.get("teamId")
        if team_id:
            url += f"?teamId={team_id.strip()}"
        
        body = {
            "name": parameters["name"].strip(),
            "blocking": parameters["blocking"],
        }
        
        path = parameters.get("path")
        if path:
            body["path"] = path
        
        details_url = parameters.get("detailsUrl")
        if details_url:
            body["detailsUrl"] = details_url
        
        external_id = parameters.get("externalId")
        if external_id:
            body["externalId"] = external_id
        
        rerequestable = parameters.get("rerequestable")
        if rerequestable is not None:
            body["rerequestable"] = rerequestable
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")