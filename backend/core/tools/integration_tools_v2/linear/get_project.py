from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class LinearGetProjectTool(BaseTool):
    name = "linear_get_project"
    description = "Get a single project by ID from Linear"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="LINEAR_ACCESS_TOKEN",
                description="Access token",
                env_var="LINEAR_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "linear",
            context=context,
            context_token_keys=("provider_token",),
            env_token_keys=("LINEAR_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "projectId": {
                    "type": "string",
                    "description": "Linear project ID",
                }
            },
            "required": ["projectId"]
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        project_id = parameters["projectId"]
        body = {
            "query": """
            query GetProject($id: String!) {
              project(id: $id) {
                id
                name
                description
                state
                priority
                startDate
                targetDate
                completedAt
                canceledAt
                archivedAt
                url
                lead {
                  id
                  name
                }
                teams {
                  nodes {
                    id
                    name
                  }
                }
              }
            }
            """,
            "variables": {
                "id": project_id,
            },
        }
        
        url = "https://api.linear.app/graphql"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code != 200:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                
                if data.get("errors"):
                    error_msg = data["errors"][0].get("message", "Failed to fetch project") if data["errors"] else "Unknown GraphQL error"
                    return ToolResult(success=False, output=response.text, error=error_msg)
                
                project = data.get("data", {}).get("project")
                if not project:
                    return ToolResult(success=False, output=response.text, error="Project not found")
                
                transformed_project = {
                    "id": project.get("id"),
                    "name": project.get("name"),
                    "description": project.get("description"),
                    "state": project.get("state"),
                    "priority": project.get("priority"),
                    "startDate": project.get("startDate"),
                    "targetDate": project.get("targetDate"),
                    "completedAt": project.get("completedAt"),
                    "canceledAt": project.get("canceledAt"),
                    "archivedAt": project.get("archivedAt"),
                    "url": project.get("url"),
                    "lead": project.get("lead", {}),
                    "teams": project.get("teams", {}).get("nodes", []),
                }
                
                return ToolResult(
                    success=True,
                    output=response.text,
                    data={"project": transformed_project}
                )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")