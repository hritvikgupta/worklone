from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class VercelListChecksTool(BaseTool):
    name = "vercel_list_checks"
    description = "List all checks for a deployment"
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
                "deploymentId": {
                    "type": "string",
                    "description": "Deployment ID to list checks for",
                },
                "teamId": {
                    "type": "string",
                    "description": "Team ID to scope the request",
                },
            },
            "required": ["deploymentId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        
        deployment_id = parameters["deploymentId"].strip()
        url = f"https://api.vercel.com/v1/deployments/{deployment_id}/checks"
        team_id = parameters.get("teamId")
        if team_id:
            url += f"?teamId={team_id.strip()}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    raw_data = response.json()
                    checks = []
                    for check in raw_data.get("checks", []):
                        checks.append({
                            "id": check.get("id"),
                            "name": check.get("name"),
                            "status": check.get("status", "registered"),
                            "conclusion": check.get("conclusion"),
                            "blocking": check.get("blocking", False),
                            "deploymentId": check.get("deploymentId"),
                            "integrationId": check.get("integrationId"),
                            "externalId": check.get("externalId"),
                            "detailsUrl": check.get("detailsUrl"),
                            "path": check.get("path"),
                            "rerequestable": check.get("rerequestable", False),
                            "createdAt": check.get("createdAt"),
                            "updatedAt": check.get("updatedAt"),
                            "startedAt": check.get("startedAt"),
                            "completedAt": check.get("completedAt"),
                        })
                    transformed = {
                        "checks": checks,
                        "count": len(checks),
                    }
                    return ToolResult(success=True, output=response.text, data=transformed)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")