from typing import Any, Dict
import httpx
import json
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GitHubDeleteProjectTool(BaseTool):
    name = "github_delete_project"
    description = "Delete a GitHub Project V2. This action is permanent and cannot be undone. Requires the project Node ID."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GITHUB_ACCESS_TOKEN",
                description="GitHub Personal Access Token with project admin permissions",
                env_var="GITHUB_ACCESS_TOKEN",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "github",
            context=context,
            context_token_keys=("provider_token",),
            env_token_keys=("GITHUB_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "Project Node ID (format: PVT_...)",
                },
            },
            "required": ["project_id"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        query = """
        mutation($projectId: ID!) {
          deleteProjectV2(input: {
            projectId: $projectId
          }) {
            projectV2 {
              id
              title
              number
              url
            }
          }
        }
        """
        json_body = {
            "query": query,
            "variables": {
                "projectId": parameters["project_id"],
            },
        }
        url = "https://api.github.com/graphql"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=json_body)
                
                if response.status_code not in [200, 201, 204]:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                if data.get("errors"):
                    err_msg = data["errors"][0].get("message", "Unknown GraphQL error")
                    output_data = {"id": "", "title": "", "number": 0, "url": ""}
                    return ToolResult(
                        success=False,
                        output=json.dumps(output_data),
                        data=output_data,
                        error=err_msg,
                    )
                
                project = data.get("data", {}).get("deleteProjectV2", {}).get("projectV2", {})
                output_data = {
                    "id": project.get("id", ""),
                    "title": project.get("title", ""),
                    "number": project.get("number"),
                    "url": project.get("url", ""),
                }
                return ToolResult(
                    success=True,
                    output=json.dumps(output_data),
                    data=output_data,
                )
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")