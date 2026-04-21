from typing import Any, Dict
import httpx
import os
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement

class GitHubGetProjectTool(BaseTool):
    name = "github_get_project"
    description = "Get detailed information about a specific GitHub Project V2 by its number. Returns project details including ID, title, description, URL, and status."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GITHUB_ACCESS_TOKEN",
                description="GitHub Personal Access Token with project read permissions",
                env_var="GITHUB_ACCESS_TOKEN",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _get_access_token(self, context: dict | None) -> str | None:
        token = None
        if context:
            token = context.get("GITHUB_ACCESS_TOKEN") or context.get("apiKey")
        if token is None:
            token = os.environ.get("GITHUB_ACCESS_TOKEN")
        if self._is_placeholder_token(token or ""):
            return None
        return token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "owner_type": {
                    "type": "string",
                    "description": 'Owner type: "org" for organization or "user" for user',
                },
                "owner_login": {
                    "type": "string",
                    "description": "Organization or user login name",
                },
                "project_number": {
                    "type": "number",
                    "description": "Project number",
                },
            },
            "required": ["owner_type", "owner_login", "project_number"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._get_access_token(context)
        if access_token is None:
            return ToolResult(success=False, output="", error="Access token not configured.")

        owner_type = parameters["owner_type"].strip().lower()
        owner_node = "organization" if owner_type == "org" else "user"
        query = f"""
            query($login: String!, $number: Int!) {{
              {owner_node}(login: $login) {{
                projectV2(number: $number) {{
                  id
                  title
                  number
                  url
                  closed
                  public
                  shortDescription
                  readme
                  createdAt
                  updatedAt
                }}
              }}
            }}
        """
        json_body = {
            "query": query.strip(),
            "variables": {
                "login": parameters["owner_login"],
                "number": parameters["project_number"],
            },
        }
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        url = "https://api.github.com/graphql"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=json_body)

                data = response.json()
                if data.get("errors"):
                    error_msg = data["errors"][0].get("message", "Unknown GraphQL error")
                    return ToolResult(success=False, output="", error=f"GraphQL Error: {error_msg}")

                data_root = data.get("data", {})
                owner_data = data_root.get("organization") or data_root.get("user")
                project = owner_data.get("projectV2") if owner_data else None

                if not project:
                    return ToolResult(
                        success=False, output="Project not found", error="Project not found"
                    )

                content = f"""Project: {project['title']} (#{project['number']})
ID: {project['id']}
URL: {project['url']}
Status: {'Closed' if project['closed'] else 'Open'}
Visibility: {'Public' if project['public'] else 'Private'}"""
                if project.get("shortDescription"):
                    content += f"\nDescription: {project['shortDescription']}"
                if project.get("createdAt"):
                    content += f"\nCreated: {project['createdAt']}"
                if project.get("updatedAt"):
                    content += f"\nUpdated: {project['updatedAt']}"

                project_data = {
                    "id": project["id"],
                    "title": project["title"],
                    "number": project["number"],
                    "url": project["url"],
                    "closed": project["closed"],
                    "public": project["public"],
                    "shortDescription": project.get("shortDescription"),
                    "readme": project.get("readme"),
                    "createdAt": project.get("createdAt"),
                    "updatedAt": project.get("updatedAt"),
                }
                return ToolResult(success=True, output=content.strip(), data=project_data)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")