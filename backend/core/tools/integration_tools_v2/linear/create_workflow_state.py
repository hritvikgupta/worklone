from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class LinearCreateWorkflowStateTool(BaseTool):
    name = "linear_create_workflow_state"
    description = "Create a new workflow state (status) in Linear"
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
                "teamId": {
                    "type": "string",
                    "description": "Team ID to create the state in",
                },
                "name": {
                    "type": "string",
                    "description": 'State name (e.g., "In Review")',
                },
                "color": {
                    "type": "string",
                    "description": "State color (hex format)",
                },
                "type": {
                    "type": "string",
                    "description": '"backlog", "unstarted", "started", "completed", or "canceled"',
                },
                "description": {
                    "type": "string",
                    "description": "State description",
                },
                "position": {
                    "type": "number",
                    "description": "Position in the workflow",
                },
            },
            "required": ["teamId", "name", "type"],
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
        
        input_data = {
            "teamId": parameters["teamId"],
            "name": parameters["name"],
            "type": parameters["type"],
        }
        
        color = parameters.get("color")
        if color is not None and color != "":
            input_data["color"] = color
        
        description = parameters.get("description")
        if description is not None and description != "":
            input_data["description"] = description
        
        position = parameters.get("position")
        if position is not None:
            input_data["position"] = float(position)
        
        body = {
            "query": """
              mutation CreateWorkflowState($input: WorkflowStateCreateInput!) {
                workflowStateCreate(input: $input) {
                  success
                  workflowState {
                    id
                    name
                    description
                    type
                    color
                    position
                    createdAt
                    updatedAt
                    archivedAt
                    team {
                      id
                      name
                    }
                  }
                }
              }
            """,
            "variables": {
                "input": input_data,
            },
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    
                    if "errors" in data and data["errors"]:
                        error_msg = data["errors"][0].get("message", "Failed to create workflow state")
                        return ToolResult(success=False, output="", error=error_msg)
                    
                    result = data.get("data", {}).get("workflowStateCreate", {})
                    if not result.get("success", False):
                        return ToolResult(success=False, output="", error="Workflow state creation was not successful")
                    
                    state = result.get("workflowState", {})
                    output_data = {"state": state}
                    return ToolResult(
                        success=True,
                        output=str(output_data),
                        data=output_data,
                    )
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")