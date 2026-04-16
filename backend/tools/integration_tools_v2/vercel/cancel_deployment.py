from typing import Any, Dict
import httpx
import os
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class VercelCancelDeploymentTool(BaseTool):
    name = "vercel_cancel_deployment"
    description = "Cancel a running Vercel deployment"
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
                "deploymentId": {
                    "type": "string",
                    "description": "The deployment ID to cancel",
                },
                "teamId": {
                    "type": "string",
                    "description": "Team ID to scope the request",
                },
            },
            "required": ["deploymentId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = (context or {}).get("VERCEL_ACCESS_TOKEN")
        if self._is_placeholder_token(access_token or ""):
            access_token = os.getenv("VERCEL_ACCESS_TOKEN")
        if self._is_placeholder_token(access_token or ""):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        deployment_id = parameters["deploymentId"].strip()
        team_id = parameters.get("teamId", "").strip()
        params_dict: Dict[str, str] = {}
        if team_id:
            params_dict["teamId"] = team_id
        url = f"https://api.vercel.com/v12/deployments/{deployment_id}/cancel"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(url, headers=headers, params=params_dict)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")