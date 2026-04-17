from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class LinearCreateProjectTool(BaseTool):
    name = "linear_create_project"
    description = "Create a new project in Linear"
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
                "teamId": {
                    "type": "string",
                    "description": "Team ID to create the project in",
                },
                "name": {
                    "type": "string",
                    "description": "Project name",
                },
                "description": {
                    "type": "string",
                    "description": "Project description",
                },
                "leadId": {
                    "type": "string",
                    "description": "User ID of the project lead",
                },
                "startDate": {
                    "type": "string",
                    "description": "Project start date (ISO format)",
                },
                "targetDate": {
                    "type": "string",
                    "description": "Project target date (ISO format)",
                },
                "priority": {
                    "type": "number",
                    "description": "Project priority (0-4)",
                },
            },
            "required": ["teamId", "name"],
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
            "teamIds": [parameters["teamId"]],
            "name": parameters["name"],
        }
        for field in ["description", "leadId", "startDate", "targetDate"]:
            value = parameters.get(field)
            if value is not None and str(value or "").strip() != "":
                input_dict[field] = value
        priority_value = parameters.get("priority")
        if priority_value is not None:
            input_dict["priority"] = float(priority_value)

        body = {
            "query": """
                mutation CreateProject($input: ProjectCreateInput!) {
                  projectCreate(input: $input) {
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
                    return ToolResult(success=False, output="", error=response.text)

                data = response.json()

                if "errors" in data and data["errors"]:
                    error_msg = data["errors"][0].get("message", "Failed to create project")
                    return ToolResult(success=False, output="", error=error_msg)

                project_create = data.get("data", {}).get("projectCreate", {})
                if not project_create.get("success"):
                    return ToolResult(success=False, output="", error="Project creation was not successful")

                return ToolResult(success=True, output=response.text, data=data)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")