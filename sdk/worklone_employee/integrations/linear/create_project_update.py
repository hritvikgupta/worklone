from typing import Any, Dict
import httpx
import json
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class LinearCreateProjectUpdateTool(BaseTool):
    name = "linear_create_project_update"
    description = "Post a status update for a project in Linear"
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
                "projectId": {
                    "type": "string",
                    "description": "Project ID to post update for",
                },
                "body": {
                    "type": "string",
                    "description": "Update message (supports Markdown)",
                },
                "health": {
                    "type": "string",
                    "description": 'Project health: "onTrack", "atRisk", or "offTrack"',
                },
            },
            "required": ["projectId", "body"],
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
        
        input_data: Dict[str, Any] = {
            "projectId": parameters["projectId"],
            "body": parameters["body"],
        }
        health = parameters.get("health")
        if health:
            input_data["health"] = health
        
        body = {
            "query": """
mutation CreateProjectUpdate($input: ProjectUpdateCreateInput!) {
  projectUpdateCreate(input: $input) {
    success
    projectUpdate {
      id
      body
      health
      createdAt
      user {
        id
        name
      }
    }
  }
}
            """.strip(),
            "variables": {
                "input": input_data,
            },
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code not in [200]:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                
                errors = data.get("errors")
                if errors:
                    error_msg = errors[0].get("message", "Failed to create project update") if isinstance(errors, list) else "Failed to create project update"
                    return ToolResult(success=False, output="", error=error_msg)
                
                result = data.get("data", {}).get("projectUpdateCreate")
                if not result or not result.get("success"):
                    return ToolResult(success=False, output="", error="Project update creation was not successful")
                
                output_data = {"update": result.get("projectUpdate", {})}
                return ToolResult(
                    success=True,
                    output=json.dumps(output_data),
                    data=output_data,
                )
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")