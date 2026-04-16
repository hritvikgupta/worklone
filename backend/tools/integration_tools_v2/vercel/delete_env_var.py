from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class VercelDeleteEnvVarTool(BaseTool):
    name = "vercel_delete_env_var"
    description = "Delete an environment variable from a Vercel project"
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
                "projectId": {
                    "type": "string",
                    "description": "Project ID or name",
                },
                "envId": {
                    "type": "string",
                    "description": "Environment variable ID to delete",
                },
                "teamId": {
                    "type": "string",
                    "description": "Team ID to scope the request",
                },
            },
            "required": ["projectId", "envId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("apiKey") or ""
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Vercel access token not configured.")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        project_id = parameters["projectId"].strip()
        env_id = parameters["envId"].strip()
        url = f"https://api.vercel.com/v9/projects/{project_id}/env/{env_id}"

        team_id = parameters.get("teamId", "").strip()
        if team_id:
            url += f"?teamId={team_id}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)

                if response.status_code in [200, 201, 204]:
                    data = None
                    try:
                        data = response.json()
                    except Exception:
                        pass
                    return ToolResult(success=True, output=response.text, data=data)
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")