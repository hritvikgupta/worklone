from typing import Any, Dict
import httpx
import json
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class LinearListProjectMilestonesTool(BaseTool):
    name = "linear_list_project_milestones"
    description = "List all milestones for a project in Linear"
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
                "projectId": {
                    "type": "string",
                    "description": "Project ID to list milestones for",
                },
                "first": {
                    "type": "number",
                    "description": "Number of milestones to return (default: 50)",
                },
                "after": {
                    "type": "string",
                    "description": "Cursor for pagination",
                },
            },
            "required": ["projectId"],
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
        query Project($id: String!, $first: Int, $after: String) {
          project(id: $id) {
            projectMilestones(first: $first, after: $after) {
              nodes {
                id
                name
                description
                targetDate
                progress
                sortOrder
                status
                createdAt
                archivedAt
                project {
                  id
                }
              }
              pageInfo {
                hasNextPage
                endCursor
              }
            }
          }
        }
        """
        variables: Dict[str, Any] = {"id": parameters["projectId"]}
        first_val = parameters.get("first")
        variables["first"] = int(first_val) if first_val is not None else 50
        after_val = parameters.get("after")
        if after_val:
            after_stripped = str(after_val).strip()
            if after_stripped:
                variables["after"] = after_stripped
        
        body = {
            "query": query,
            "variables": variables,
        }
        url = "https://api.linear.app/graphql"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code not in [200, 201, 204]:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                if data.get("errors"):
                    error_msg = data["errors"][0].get("message", "Failed to list project milestones")
                    return ToolResult(success=False, output="", error=error_msg)
                
                project_milestones_data = data.get("data", {}).get("project", {}).get("projectMilestones", {})
                nodes = project_milestones_data.get("nodes", [])
                milestones = []
                for node in nodes:
                    proj = node.get("project", {})
                    project_id = proj.get("id")
                    milestone_dict = node.copy()
                    milestone_dict["projectId"] = project_id
                    milestone_dict.pop("project", None)
                    milestones.append(milestone_dict)
                
                page_info_data = project_milestones_data.get("pageInfo", {})
                page_info = {
                    "hasNextPage": page_info_data.get("hasNextPage", False),
                    "endCursor": page_info_data.get("endCursor"),
                }
                
                processed_data = {
                    "projectMilestones": milestones,
                    "pageInfo": page_info,
                }
                output_str = json.dumps(processed_data)
                return ToolResult(success=True, output=output_str, data=processed_data)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")