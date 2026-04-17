from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class VercelUpdateEnvVarTool(BaseTool):
    name = "vercel_update_env_var"
    description = "Update an environment variable for a Vercel project"
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
        return context.get("VERCEL_ACCESS_TOKEN", "") if context else ""

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
                    "description": "Environment variable ID to update",
                },
                "key": {
                    "type": "string",
                    "description": "New variable name",
                },
                "value": {
                    "type": "string",
                    "description": "New variable value",
                },
                "target": {
                    "type": "string",
                    "description": "Comma-separated list of target environments (production, preview, development)",
                },
                "type": {
                    "type": "string",
                    "description": "Variable type: system, secret, encrypted, plain, or sensitive",
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
            "required": ["projectId", "envId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        project_id = parameters["projectId"].strip()
        env_id = parameters["envId"].strip()

        body: Dict[str, Any] = {}
        if parameters.get("key"):
            body["key"] = parameters["key"]
        if parameters.get("value"):
            body["value"] = parameters["value"]
        if parameters.get("type"):
            body["type"] = parameters["type"]
        if parameters.get("gitBranch"):
            body["gitBranch"] = parameters["gitBranch"]
        if parameters.get("comment"):
            body["comment"] = parameters["comment"]
        target_str = parameters.get("target")
        if target_str:
            body["target"] = [t.strip() for t in str(target_str).split(",")]

        query_params: Dict[str, str] = {}
        team_id = parameters.get("teamId")
        if team_id:
            query_params["teamId"] = str(team_id).strip()

        url = f"https://api.vercel.com/v9/projects/{project_id}/env/{env_id}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(url, headers=headers, json=body, params=query_params)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")