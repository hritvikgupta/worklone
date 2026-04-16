from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class VercelGetEnvVarsTool(BaseTool):
    name = "vercel_get_env_vars"
    description = "Retrieve environment variables for a Vercel project"
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
                "teamId": {
                    "type": "string",
                    "description": "Team ID to scope the request",
                },
            },
            "required": ["projectId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = context.get("VERCEL_ACCESS_TOKEN") if context else None
        
        if self._is_placeholder_token(access_token or ""):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        project_id = parameters["projectId"].strip()
        team_id = parameters.get("teamId", "").strip()
        
        url = f"https://api.vercel.com/v10/projects/{project_id}/env"
        if team_id:
            url += f"?teamId={team_id}"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    envs = []
                    if data.get("envs"):
                        for e in data["envs"]:
                            envs.append({
                                "id": e.get("id"),
                                "key": e.get("key"),
                                "value": e.get("value", ""),
                                "type": e.get("type", "plain"),
                                "target": e.get("target", []),
                                "gitBranch": e.get("gitBranch"),
                                "comment": e.get("comment"),
                            })
                    output_data = {
                        "envs": envs,
                        "count": len(envs),
                    }
                    return ToolResult(success=True, output=response.text, data=output_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")