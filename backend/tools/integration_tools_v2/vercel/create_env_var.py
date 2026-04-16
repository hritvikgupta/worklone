from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class VercelCreateEnvVarTool(BaseTool):
    name = "vercel_create_env_var"
    description = "Create an environment variable for a Vercel project"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="VERCEL_API_KEY",
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
                "projectId": {
                    "type": "string",
                    "description": "Project ID or name",
                },
                "key": {
                    "type": "string",
                    "description": "Environment variable name",
                },
                "value": {
                    "type": "string",
                    "description": "Environment variable value",
                },
                "target": {
                    "type": "string",
                    "description": "Comma-separated list of target environments (production, preview, development)",
                },
                "type": {
                    "type": "string",
                    "description": "Variable type: system, secret, encrypted, plain, or sensitive (default: plain)",
                },
                "gitBranch": {
                    "type": "string",
                    "description": "Git branch to associate with the variable (requires target to include preview)",
                },
                "comment": {
                    "type": "string",
                    "description": "Comment to add context to the variable (max 500 characters)",
                },
                "teamId": {
                    "type": "string",
                    "description": "Team ID to scope the request",
                },
            },
            "required": ["projectId", "key", "value", "target"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("VERCEL_API_KEY") if context else None
        
        if self._is_placeholder_token(api_key or ""):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        project_id = parameters["projectId"].strip()
        key = parameters["key"]
        value = parameters["value"]
        target_str = parameters["target"]
        target = [t.strip() for t in target_str.split(",")]
        type_ = parameters.get("type", "plain")
        git_branch = parameters.get("gitBranch")
        comment = parameters.get("comment")
        team_id = parameters.get("teamId")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        url = f"https://api.vercel.com/v10/projects/{project_id}/env"
        params = None
        if team_id:
            params = {"teamId": team_id.strip()}
        
        body = {
            "key": key,
            "value": value,
            "target": target,
            "type": type_,
        }
        if git_branch:
            body["gitBranch"] = git_branch
        if comment:
            body["comment"] = comment
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body, params=params)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")