from typing import Any, Dict
import httpx
import json
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class LinearCreateProjectMilestoneTool(BaseTool):
    name = "linear_create_project_milestone"
    description = "Create a new project milestone in Linear"
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
            context_token_keys=("access_token",),
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
                    "description": "Project ID",
                },
                "name": {
                    "type": "string",
                    "description": "Milestone name",
                },
                "description": {
                    "type": "string",
                    "description": "Milestone description",
                },
                "targetDate": {
                    "type": "string",
                    "description": "Target date (ISO 8601)",
                },
            },
            "required": ["projectId", "name"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        input_data = {
            "projectId": parameters["projectId"],
            "name": parameters["name"],
        }
        description = parameters.get("description")
        if description is not None and description != "":
            input_data["description"] = description
        target_date = parameters.get("targetDate")
        if target_date is not None and target_date != "":
            input_data["targetDate"] = target_date
        
        json_body = {
            "query": """
            mutation ProjectMilestoneCreate($input: ProjectMilestoneCreateInput!) {
              projectMilestoneCreate(input: $input) {
                success
                projectMilestone {
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
              }
            }
            """,
            "variables": {
                "input": input_data,
            },
        }
        
        url = "https://api.linear.app/graphql"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=json_body)
                response.raise_for_status()
                data = response.json()
                
                if "errors" in data and data["errors"]:
                    error_msg = data["errors"][0].get("message", "Failed to create project milestone")
                    return ToolResult(success=False, output="", error=error_msg)
                
                result = data.get("data", {}).get("projectMilestoneCreate", {})
                if not result.get("success"):
                    return ToolResult(success=False, output="", error="Project milestone creation was not successful")
                
                milestone = result.get("projectMilestone")
                if not milestone:
                    return ToolResult(success=False, output="", error="No project milestone returned from API")
                
                project_id = None
                project = milestone.get("project")
                if project:
                    project_id = project.get("id")
                
                transformed_milestone = {
                    **milestone,
                    "projectId": project_id,
                    "project": None,
                }
                
                output_data = {"projectMilestone": transformed_milestone}
                return ToolResult(
                    success=True,
                    output=json.dumps(output_data),
                    data=output_data,
                )
        except httpx.HTTPStatusError as e:
            return ToolResult(success=False, output="", error=f"HTTP error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")