from typing import Any, Dict
import httpx
import json
from urllib.parse import urlencode
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class VercelCreateDeploymentTool(BaseTool):
    name = "vercel_create_deployment"
    description = "Create a new deployment or redeploy an existing one"
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
            context_token_keys=("apiKey",),
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
                    "description": "Project name for the deployment"
                },
                "project": {
                    "type": "string",
                    "description": "Project ID (overrides name for project lookup)"
                },
                "deploymentId": {
                    "type": "string",
                    "description": "Existing deployment ID to redeploy"
                },
                "target": {
                    "type": "string",
                    "description": "Target environment: production, staging, or a custom environment identifier"
                },
                "gitSource": {
                    "type": "string",
                    "description": 'JSON string defining the Git Repository source to deploy (e.g. {"type":"github","repo":"owner/repo","ref":"main"})'
                },
                "forceNew": {
                    "type": "string",
                    "description": "Forces a new deployment even if there is a previous similar deployment (0 or 1)"
                },
                "teamId": {
                    "type": "string",
                    "description": "Team ID to scope the request"
                },
            },
            "required": ["name"]
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        query_params: dict[str, str] = {}
        force_new = parameters.get("forceNew")
        if force_new:
            query_params["forceNew"] = str(force_new)
        team_id = parameters.get("teamId")
        if team_id:
            query_params["teamId"] = str(team_id).strip()
        
        url = "https://api.vercel.com/v13/deployments"
        if query_params:
            url += "?" + urlencode(query_params)
        
        body: dict[str, Any] = {
            "name": str(parameters["name"]).strip(),
        }
        project = parameters.get("project")
        if project:
            body["project"] = str(project).strip()
        deployment_id = parameters.get("deploymentId")
        if deployment_id:
            body["deploymentId"] = str(deployment_id).strip()
        target = parameters.get("target")
        if target:
            body["target"] = target
        git_source = parameters.get("gitSource")
        if git_source:
            try:
                body["gitSource"] = json.loads(git_source)
            except json.JSONDecodeError:
                body["gitSource"] = git_source
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")