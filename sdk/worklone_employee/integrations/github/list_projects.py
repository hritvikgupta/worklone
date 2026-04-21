from typing import Any, Dict
import httpx
import json
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class GitHubListProjectsTool(BaseTool):
    name = "github_list_projects"
    description = "List GitHub Projects V2 for an organization or user. Returns up to 20 projects with their details including ID, title, number, URL, and status."
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

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "github",
            context=context,
            context_token_keys=("github_token",),
            env_token_keys=("GITHUB_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

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
            },
            "required": ["owner_type", "owner_login"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        owner_type = parameters["owner_type"]
        owner_login = parameters["owner_login"]
        ownerType = "organization" if owner_type == "org" else "user"
        query = f"""
query($login: String!) {{
  {ownerType}(login: $login) {{
    projectsV2(first: 20) {{
      nodes {{
        id
        title
        number
        url
        closed
        public
        shortDescription
      }}
      totalCount
    }}
  }}
}}
        """.strip()
        body = {
            "query": query,
            "variables": {
                "login": owner_login,
            },
        }
        url = "https://api.github.com/graphql"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code != 200:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"HTTP {response.status_code}: {response.text}",
                    )
                
                try:
                    resp_data = response.json()
                except Exception:
                    return ToolResult(
                        success=False,
                        output=response.text,
                        error="Invalid JSON response",
                    )
                
                if "errors" in resp_data and resp_data["errors"]:
                    error_msg = resp_data["errors"][0].get("message", "Unknown GraphQL error")
                    return ToolResult(
                        success=False,
                        output="",
                        error=error_msg,
                        data={"items": [], "totalCount": 0},
                    )
                
                data_path = resp_data.get("data", {})
                owner_data = data_path.get("organization") or data_path.get("user")
                if not owner_data:
                    return ToolResult(
                        success=False,
                        output="",
                        error="No organization or user found",
                        data={"items": [], "totalCount": 0},
                    )
                
                projects_data = owner_data.get("projectsV2")
                if not projects_data:
                    return ToolResult(
                        success=False,
                        output="",
                        error="No projects data found",
                        data={"items": [], "totalCount": 0},
                    )
                
                items = [
                    {
                        "id": project.get("id"),
                        "title": project.get("title"),
                        "number": project.get("number"),
                        "url": project.get("url"),
                        "closed": project.get("closed"),
                        "public": project.get("public"),
                        "shortDescription": project.get("shortDescription"),
                    }
                    for project in projects_data.get("nodes", [])
                ]
                total_count = projects_data.get("totalCount", 0)
                output_data = {"items": items, "totalCount": total_count}
                
                return ToolResult(
                    success=True,
                    output=json.dumps(output_data, indent=2),
                    data=output_data,
                )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")