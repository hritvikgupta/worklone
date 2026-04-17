from typing import Any, Dict
import httpx
from urllib.parse import urlencode
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class VercelUpdateProjectTool(BaseTool):
    name = "vercel_update_project"
    description = "Update an existing Vercel project"
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

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "projectId": {
                    "type": "string",
                    "description": "Project ID or name",
                },
                "name": {
                    "type": "string",
                    "description": "New project name",
                },
                "framework": {
                    "type": "string",
                    "description": "Project framework (e.g. nextjs, remix, vite)",
                },
                "buildCommand": {
                    "type": "string",
                    "description": "Custom build command",
                },
                "outputDirectory": {
                    "type": "string",
                    "description": "Custom output directory",
                },
                "installCommand": {
                    "type": "string",
                    "description": "Custom install command",
                },
                "teamId": {
                    "type": "string",
                    "description": "Team ID to scope the request",
                },
            },
            "required": ["projectId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = context.get("VERCEL_ACCESS_TOKEN") if context else None
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        project_id = parameters["projectId"].strip()
        url = f"https://api.vercel.com/v9/projects/{project_id}"
        
        query_params = {}
        team_id = parameters.get("teamId", "").strip()
        if team_id:
            query_params["teamId"] = team_id
        if query_params:
            url += "?" + urlencode(query_params)
        
        body = {}
        fields = ["name", "framework", "buildCommand", "outputDirectory", "installCommand"]
        for field in fields:
            val = parameters.get(field, "").strip()
            if val:
                body[field] = val
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")