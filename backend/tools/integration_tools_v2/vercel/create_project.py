from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class VercelCreateProjectTool(BaseTool):
    name = "vercel_create_project"
    description = "Create a new Vercel project"
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
        connection = await resolve_oauth_connection(
            "vercel",
            context=context,
            context_token_keys=("vercel_access_token",),
            env_token_keys=("VERCEL_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Project name",
                },
                "framework": {
                    "type": "string",
                    "description": "Project framework (e.g. nextjs, remix, vite)",
                },
                "gitRepository": {
                    "type": "object",
                    "description": "Git repository connection object with type and repo",
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
            "required": ["name"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = "https://api.vercel.com/v11/projects"
        query_params: Dict[str, str] = {}
        team_id = parameters.get("teamId")
        if team_id:
            query_params["teamId"] = str(team_id).strip()
        
        body: Dict[str, Any] = {
            "name": parameters["name"].strip(),
        }
        framework = parameters.get("framework")
        if framework:
            body["framework"] = str(framework).strip()
        git_repository = parameters.get("gitRepository")
        if git_repository:
            body["gitRepository"] = git_repository
        build_command = parameters.get("buildCommand")
        if build_command:
            body["buildCommand"] = str(build_command).strip()
        output_directory = parameters.get("outputDirectory")
        if output_directory:
            body["outputDirectory"] = str(output_directory).strip()
        install_command = parameters.get("installCommand")
        if install_command:
            body["installCommand"] = str(install_command).strip()
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url, headers=headers, json=body, params=query_params
                )
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")