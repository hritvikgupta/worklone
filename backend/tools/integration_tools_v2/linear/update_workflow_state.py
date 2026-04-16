from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class LinearUpdateWorkflowStateTool(BaseTool):
    name = "linear_update_workflow_state"
    description = "Update an existing workflow state in Linear"
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
                "stateId": {
                    "type": "string",
                    "description": "Workflow state ID to update",
                },
                "name": {
                    "type": "string",
                    "description": "New state name",
                },
                "color": {
                    "type": "string",
                    "description": "New state color (hex format)",
                },
                "description": {
                    "type": "string",
                    "description": "New state description",
                },
                "position": {
                    "type": "number",
                    "description": "New position in workflow",
                },
            },
            "required": ["stateId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        input_data: Dict[str, Any] = {}
        name = parameters.get("name")
        if name is not None and name != "":
            input_data["name"] = name
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
                mutation UpdateWorkflowState($id: String!, $input: WorkflowStateUpdateInput!) {
                  workflowStateUpdate(id: $id, input: $input) {
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
                "id": parameters["stateId"],
                "input": input_data,
            },
        }

        url = "https://api.linear.app/graphql"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                data = response.json()
                ws_update = data.get("data", {}).get("workflowStateUpdate", {})
                if (
                    response.status_code in [200, 201, 204]
                    and not data.get("errors")
                    and ws_update.get("success")
                ):
                    return ToolResult(success=True, output=response.text, data=data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")