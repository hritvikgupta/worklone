from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class LinearUpdateProjectTool(BaseTool):
    name = "linear_update_project"
    description = "Update an existing project in Linear"
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
            context_token_keys=("provider_token",),
            env_token_keys=("LINEAR_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def _build_input(self, parameters: dict) -> dict[str, Any]:
        input_: dict[str, Any] = {}
        string_fields = ["name", "description", "state", "leadId", "startDate", "targetDate"]
        for field in string_fields:
            value = parameters.get(field)
            if value is not None and value != "":
                input_[field] = value
        priority = parameters.get("priority")
        if priority is not None:
            input_["priority"] = int(priority)
        return input_

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "projectId": {
                    "type": "string",
                    "description": "Project ID to update",
                },
                "name": {
                    "type": "string",
                    "description": "New project name",
                },
                "description": {
                    "type": "string",
                    "description": "New project description",
                },
                "state": {
                    "type": "string",
                    "description": "Project state (planned, started, completed, canceled)",
                },
                "leadId": {
                    "type": "string",
                    "description": "User ID of the project lead",
                },
                "startDate": {
                    "type": "string",
                    "description": "Project start date (ISO format: YYYY-MM-DD)",
                },
                "targetDate": {
                    "type": "string",
                    "description": "Project target date (ISO format: YYYY-MM-DD)",
                },
                "priority": {
                    "type": "number",
                    "description": "Project priority (0=No priority, 1=Urgent, 2=High, 3=Normal, 4=Low)",
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
        
        url = "https://api.linear.app/graphql"
        
        project_id = parameters["projectId"]
        input_data = self._build_input(parameters)
        
        query = """
        mutation UpdateProject($id: String!, $input: ProjectUpdateInput!) {
          projectUpdate(id: $id, input: $input) {
            success
            project {
              id
              name
              description
              state
              priority
              startDate
              targetDate
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
        }
        """
        
        json_body = {
            "query": query,
            "variables": {
                "id": project_id,
                "input": input_data,
            },
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=json_body)
                
                if response.status_code != 200:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                
                if data.get("errors"):
                    error_msg = data["errors"][0].get("message", str(data["errors"]))
                    return ToolResult(success=False, output="", error=error_msg)
                
                result = data.get("data", {}).get("projectUpdate")
                if not result or not result.get("success"):
                    return ToolResult(success=False, output="", error="Project update was not successful")
                
                project = result.get("project", {})
                output_data = {
                    "project": {
                        "id": project.get("id"),
                        "name": project.get("name"),
                        "description": project.get("description"),
                        "state": project.get("state"),
                        "priority": project.get("priority"),
                        "startDate": project.get("startDate"),
                        "targetDate": project.get("targetDate"),
                        "url": project.get("url"),
                        "lead": project.get("lead"),
                        "teams": project.get("teams", {}).get("nodes", []) if project.get("teams") else [],
                    },
                }
                output_str = json.dumps(output_data)
                return ToolResult(success=True, output=output_str, data=output_data)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")