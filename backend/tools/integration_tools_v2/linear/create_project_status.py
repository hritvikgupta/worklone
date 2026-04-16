from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class LinearCreateProjectStatusTool(BaseTool):
    name = "linear_create_project_status"
    description = "Create a new project status in Linear"
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
                "name": {
                    "type": "string",
                    "description": "Project status name",
                },
                "type": {
                    "type": "string",
                    "description": 'Status type: "backlog", "planned", "started", "paused", "completed", or "canceled"',
                },
                "color": {
                    "type": "string",
                    "description": "Status color (hex code)",
                },
                "position": {
                    "type": "number",
                    "description": "Position in status list (e.g. 0, 1, 2...)",
                },
                "description": {
                    "type": "string",
                    "description": "Status description",
                },
                "indefinite": {
                    "type": "boolean",
                    "description": "Whether the status is indefinite",
                },
            },
            "required": ["name", "type", "color", "position"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        input_dict: Dict[str, Any] = {
            "name": parameters["name"],
            "type": parameters["type"],
            "color": parameters["color"],
            "position": parameters["position"],
        }

        description = parameters.get("description")
        if description is not None and description != "":
            input_dict["description"] = description

        indefinite = parameters.get("indefinite")
        if indefinite is not None:
            input_dict["indefinite"] = indefinite

        body = {
            "query": """
                mutation ProjectStatusCreate($input: ProjectStatusCreateInput!) {
                  projectStatusCreate(input: $input) {
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
                "input": input_dict,
            },
        }

        url = "https://api.linear.app/graphql"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code != 200:
                    return ToolResult(
                        success=False, output="", error=f"HTTP {response.status_code}: {response.text}"
                    )

                data = response.json()

                if "errors" in data and data["errors"]:
                    error_msg = data["errors"][0].get("message", "Failed to create project status")
                    return ToolResult(success=False, output="", error=error_msg)

                result = data.get("data", {}).get("projectStatusCreate", {})
                if not result.get("success", False):
                    return ToolResult(
                        success=False,
                        output="",
                        error="Project status creation was not successful",
                    )

                status = result.get("status", {})
                output_data = {"projectStatus": status}
                return ToolResult(
                    success=True,
                    output=str(output_data),
                    data=output_data,
                )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")