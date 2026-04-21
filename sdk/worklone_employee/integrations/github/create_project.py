from typing import Any, Dict
import httpx
import base64
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class GitHubCreateProjectTool(BaseTool):
    name = "github_create_project"
    description = "Create a new GitHub Project V2. Requires the owner Node ID (not login name). Returns the created project with ID, title, and URL."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GITHUB_ACCESS_TOKEN",
                description="GitHub Personal Access Token with project write permissions",
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
                "owner_id": {
                    "type": "string",
                    "description": "Owner Node ID (format: PVT_... or MDQ6...). Use GitHub GraphQL API to get this ID from organization or user login.",
                },
                "title": {
                    "type": "string",
                    "description": "Project title",
                },
            },
            "required": ["owner_id", "title"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = "https://api.github.com/graphql"
        
        query = """
        mutation($ownerId: ID!, $title: String!) {
          createProjectV2(input: {
            ownerId: $ownerId
            title: $title
          }) {
            projectV2 {
              id
              title
              number
              url
              closed
              public
              shortDescription
            }
          }
        }
        """.strip()
        
        json_body = {
            "query": query,
            "variables": {
                "ownerId": parameters["owner_id"],
                "title": parameters["title"],
            },
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=json_body)
                
                if response.status_code not in [200, 201, 204]:
                    return ToolResult(success=False, output="", error=response.text)
                
                try:
                    data = response.json()
                except Exception as json_err:
                    return ToolResult(success=False, output="", error=f"Invalid JSON response: {str(json_err)}")
                
                if data.get("errors"):
                    err = data["errors"][0]
                    msg = err.get("message", str(err))
                    return ToolResult(success=False, output="", error=f"GraphQL Error: {msg}")
                
                project = data.get("data", {}).get("createProjectV2", {}).get("projectV2")
                if not project or not project.get("id"):
                    return ToolResult(success=False, output="", error="Failed to create project")
                
                return ToolResult(success=True, output=response.text, data=data)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")