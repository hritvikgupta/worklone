from typing import Any, Dict, List
import httpx
import json
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class LinearListProjectsTool(BaseTool):
    name = "linear_list_projects"
    description = "List projects in Linear with optional filtering"
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
                "teamId": {
                    "type": "string",
                    "description": "Filter by team ID",
                },
                "includeArchived": {
                    "type": "boolean",
                    "description": "Include archived projects",
                },
                "first": {
                    "type": "number",
                    "description": "Number of projects to return (default: 50)",
                },
                "after": {
                    "type": "string",
                    "description": "Cursor for pagination",
                },
            },
            "required": [],
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
        
        first = parameters.get("first")
        variables = {
            "first": int(first) if first is not None else 50,
            "includeArchived": parameters.get("includeArchived", False),
        }
        after = parameters.get("after")
        if after:
            variables["after"] = str(after).strip()
        
        body = {
            "query": """
            query ListProjects($first: Int, $after: String, $includeArchived: Boolean) {
              projects(first: $first, after: $after, includeArchived: $includeArchived) {
                nodes {
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
                pageInfo {
                  hasNextPage
                  endCursor
                }
              }
            }
            """,
            "variables": variables,
        }
        
        team_id = parameters.get("teamId")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code not in [200, 201, 204]:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                
                if data.get("errors"):
                    error_msg = data["errors"][0].get("message", "Failed to list projects") if data["errors"] else "Unknown GraphQL error"
                    return ToolResult(success=False, output="", error=error_msg)
                
                projects_result = data["data"]["projects"]
                projects = []
                for node in projects_result["nodes"]:
                    project = {
                        "id": node["id"],
                        "name": node["name"],
                        "description": node["description"],
                        "state": node["state"],
                        "priority": node.get("priority"),
                        "startDate": node.get("startDate"),
                        "targetDate": node.get("targetDate"),
                        "completedAt": node.get("completedAt"),
                        "canceledAt": node.get("canceledAt"),
                        "archivedAt": node.get("archivedAt"),
                        "url": node["url"],
                        "lead": node.get("lead", {}),
                        "teams": node.get("teams", {}).get("nodes", []) if node.get("teams") else [],
                    }
                    projects.append(project)
                
                if team_id:
                    projects = [p for p in projects if any(team["id"] == team_id for team in p["teams"])]
                
                page_info = {
                    "hasNextPage": projects_result["pageInfo"]["hasNextPage"],
                    "endCursor": projects_result["pageInfo"]["endCursor"],
                }
                
                transformed = {
                    "projects": projects,
                    "pageInfo": page_info,
                }
                output_str = json.dumps(transformed)
                
                return ToolResult(success=True, output=output_str, data=transformed)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")