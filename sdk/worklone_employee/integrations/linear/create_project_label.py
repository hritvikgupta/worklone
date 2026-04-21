from typing import Any, Dict
import httpx
import json
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class LinearCreateProjectLabelTool(BaseTool):
    name = "linear_create_project_label"
    description = "Create a new project label in Linear"
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
                "name": {
                    "type": "string",
                    "description": "Project label name",
                },
                "color": {
                    "type": "string",
                    "description": "Label color (hex code)",
                },
                "description": {
                    "type": "string",
                    "description": "Label description",
                },
                "isGroup": {
                    "type": "boolean",
                    "description": "Whether this is a label group",
                },
                "parentId": {
                    "type": "string",
                    "description": "Parent label group ID",
                },
            },
            "required": ["name"],
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
            "name": parameters["name"],
        }
        color = parameters.get("color")
        if color is not None and color != "":
            input_data["color"] = color
        description = parameters.get("description")
        if description is not None and description != "":
            input_data["description"] = description
        is_group = parameters.get("isGroup")
        if is_group is not None:
            input_data["isGroup"] = is_group
        parent_id = parameters.get("parentId")
        if parent_id is not None and parent_id != "":
            input_data["parentId"] = parent_id
        
        body = {
            "query": """
                mutation ProjectLabelCreate($input: ProjectLabelCreateInput!) {
                  projectLabelCreate(input: $input) {
                    success
                    projectLabel {
                      id
                      name
                      description
                      color
                      isGroup
                      createdAt
                      updatedAt
                      archivedAt
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
                
                if response.status_code not in [200]:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"HTTP {response.status_code}: {response.text}",
                    )
                
                data = response.json()
                
                errors = data.get("errors")
                if errors:
                    error_msg = errors[0].get("message", "Failed to create project label")
                    return ToolResult(success=False, output="", error=error_msg)
                
                result = data["data"]["projectLabelCreate"]
                if not result["success"]:
                    return ToolResult(
                        success=False,
                        output="",
                        error="Project label creation was not successful",
                    )
                
                output_data = {"projectLabel": result["projectLabel"]}
                return ToolResult(
                    success=True,
                    output=json.dumps(output_data),
                    data=output_data,
                )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")