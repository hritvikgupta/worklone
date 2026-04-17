from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class LinearUpdateProjectLabelTool(BaseTool):
    name = "linear_update_project_label"
    description = "Update a project label in Linear"
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
                "labelId": {
                    "type": "string",
                    "description": "Project label ID to update",
                },
                "name": {
                    "type": "string",
                    "description": "Updated label name",
                },
                "color": {
                    "type": "string",
                    "description": "Updated label color",
                },
                "description": {
                    "type": "string",
                    "description": "Updated description",
                },
            },
            "required": ["labelId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        input_ = {}
        name = parameters.get("name")
        if name is not None and name != "":
            input_["name"] = name
        color = parameters.get("color")
        if color is not None and color != "":
            input_["color"] = color
        description = parameters.get("description")
        if description is not None and description != "":
            input_["description"] = description

        query = """
          mutation ProjectLabelUpdate($id: String!, $input: ProjectLabelUpdateInput!) {
            projectLabelUpdate(id: $id, input: $input) {
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
        """
        body = {
            "query": query,
            "variables": {
                "id": parameters["labelId"],
                "input": input_,
            },
        }
        url = "https://api.linear.app/graphql"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code != 200:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                if data.get("errors"):
                    error_msg = data["errors"][0].get("message", "Failed to update project label") if data["errors"] else "Unknown GraphQL error"
                    return ToolResult(success=False, output="", error=error_msg)
                
                result = data.get("data", {}).get("projectLabelUpdate")
                if result is None:
                    return ToolResult(success=False, output="", error="Invalid response structure")
                
                if not result.get("success"):
                    return ToolResult(success=False, output="", error="Update failed")
                
                return ToolResult(success=True, output=response.text, data=data)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")