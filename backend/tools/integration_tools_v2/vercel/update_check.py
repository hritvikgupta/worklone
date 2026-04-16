from typing import Any, Dict
import httpx
import json
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class VercelUpdateCheckTool(BaseTool):
    name = "vercel_update_check"
    description = "Update an existing deployment check"
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
                    "description": "Deployment ID the check belongs to",
                },
                "checkId": {
                    "type": "string",
                    "description": "Check ID to update",
                },
                "name": {
                    "type": "string",
                    "description": "Updated name of the check",
                },
                "status": {
                    "type": "string",
                    "description": "Updated status: running or completed",
                },
                "conclusion": {
                    "type": "string",
                    "description": "Check conclusion: canceled, failed, neutral, succeeded, or skipped",
                },
                "detailsUrl": {
                    "type": "string",
                    "description": "URL with details about the check",
                },
                "externalId": {
                    "type": "string",
                    "description": "External identifier for the check",
                },
                "path": {
                    "type": "string",
                    "description": "Page path being checked",
                },
                "output": {
                    "type": "string",
                    "description": "JSON string with check output metrics",
                },
                "teamId": {
                    "type": "string",
                    "description": "Team ID to scope the request",
                },
            },
            "required": ["deploymentId", "checkId"],
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
        check_id = parameters["checkId"].strip()
        url = f"https://api.vercel.com/v1/deployments/{deployment_id}/checks/{check_id}"
        
        team_id = parameters.get("teamId")
        if team_id:
            url += f"?teamId={team_id.strip()}"
        
        body = {}
        name = parameters.get("name")
        if name:
            body["name"] = name.strip()
        status = parameters.get("status")
        if status:
            body["status"] = status
        conclusion = parameters.get("conclusion")
        if conclusion:
            body["conclusion"] = conclusion
        details_url = parameters.get("detailsUrl")
        if details_url:
            body["detailsUrl"] = details_url
        external_id = parameters.get("externalId")
        if external_id:
            body["externalId"] = external_id
        path = parameters.get("path")
        if path:
            body["path"] = path
        output = parameters.get("output")
        if output:
            try:
                body["output"] = json.loads(output)
            except:
                body["output"] = output
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")