from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class LinearDeleteProjectMilestoneTool(BaseTool):
    name = "linear_delete_project_milestone"
    description = "Delete a project milestone in Linear"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="LINEAR_ACCESS_TOKEN",
                description="Access token for Linear",
                env_var="LINEAR_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "linear",
            context=context,
            context_token_keys=("linear_token",),
            env_token_keys=("LINEAR_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "milestoneId": {
                    "type": "string",
                    "description": "Project milestone ID to delete",
                },
            },
            "required": ["milestoneId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = "https://api.linear.app/graphql"
        
        json_body = {
            "query": """
                mutation ProjectMilestoneDelete($id: String!) {
                  projectMilestoneDelete(id: $id) {
                    success
                  }
                }
            """,
            "variables": {
                "id": parameters["milestoneId"],
            },
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=json_body)
                
                if response.status_code != 200:
                    return ToolResult(success=False, output="", error=f"HTTP {response.status_code}: {response.text}")
                
                data = response.json()
                
                if data.get("errors"):
                    error_msg = data["errors"][0].get("message", "Failed to delete project milestone")
                    return ToolResult(success=False, output="", error=error_msg)
                
                result = data.get("data", {}).get("projectMilestoneDelete", {})
                if not result:
                    return ToolResult(success=False, output="", error="No result data in response")
                
                tool_success = result.get("success", False)
                output_data = {"success": tool_success}
                
                return ToolResult(success=tool_success, output=str(output_data), data=output_data)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")