from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class LinearUpdateProjectStatusTool(BaseTool):
    name = "linear_update_project_status"
    description = "Update a project status in Linear"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="LINEAR_ACCESS_TOKEN",
                description="Linear OAuth access token",
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
                "statusId": {
                    "type": "string",
                    "description": "Project status ID to update",
                },
                "name": {
                    "type": "string",
                    "description": "Updated status name",
                },
                "color": {
                    "type": "string",
                    "description": "Updated status color",
                },
                "description": {
                    "type": "string",
                    "description": "Updated description",
                },
                "indefinite": {
                    "type": "boolean",
                    "description": "Updated indefinite flag",
                },
                "position": {
                    "type": "number",
                    "description": "Updated position",
                },
            },
            "required": ["statusId"],
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

        status_id = parameters["statusId"]
        input_: Dict[str, Any] = {}
        name = parameters.get("name")
        if name is not None and name != "":
            input_["name"] = name
        color = parameters.get("color")
        if color is not None and color != "":
            input_["color"] = color
        description = parameters.get("description")
        if description is not None and description != "":
            input_["description"] = description
        indefinite = parameters.get("indefinite")
        if indefinite is not None:
            input_["indefinite"] = indefinite
        position = parameters.get("position")
        if position is not None:
            input_["position"] = position

        json_body = {
            "query": """
mutation ProjectStatusUpdate($id: String!, $input: ProjectStatusUpdateInput!) {
  projectStatusUpdate(id: $id, input: $input) {
    success
    status {
      id
      name
      description
      color
      indefinite
      position
      type
      createdAt
      updatedAt
      archivedAt
    }
  }
}
            """,
            "variables": {
                "id": status_id,
                "input": input_,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=json_body)

            if response.status_code != 200:
                return ToolResult(
                    success=False, output="", error=f"HTTP {response.status_code}: {response.text}"
                )

            try:
                data = response.json()
            except Exception:
                return ToolResult(
                    success=False, output=response.text, error="Invalid JSON response"
                )

            if data.get("errors"):
                error_msg = data["errors"][0].get("message", "Unknown GraphQL error")
                return ToolResult(success=False, output="", error=error_msg)

            result = data.get("data", {}).get("projectStatusUpdate", {})
            if not result.get("success", False):
                return ToolResult(
                    success=False, output="", error="Failed to update project status"
                )

            status = result.get("status", {})
            return ToolResult(success=True, output=str(status), data=status)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")