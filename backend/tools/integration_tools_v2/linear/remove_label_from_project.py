from typing import Any, Dict
import httpx
import json
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class LinearRemoveLabelFromProjectTool(BaseTool):
    name = "linear_remove_label_from_project"
    description = "Remove a label from a project in Linear"
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
                    "description": "Project ID",
                },
                "labelId": {
                    "type": "string",
                    "description": "Label ID to remove",
                },
            },
            "required": ["projectId", "labelId"],
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
        body = {
            "query": """
                mutation ProjectRemoveLabel($id: String!, $labelId: String!) {
                  projectRemoveLabel(id: $id, labelId: $labelId) {
                    success
                    project {
                      id
                    }
                  }
                }
            """,
            "variables": {
                "id": parameters["projectId"],
                "labelId": parameters["labelId"],
            },
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code not in [200, 201]:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                
                if "errors" in data and data["errors"]:
                    error_msg = data["errors"][0].get("message", "Failed to remove label from project")
                    return ToolResult(success=False, output="", error=error_msg)
                
                result = data.get("data", {}).get("projectRemoveLabel", {})
                output_data = {
                    "success": result.get("success", False),
                    "projectId": result.get("project", {}).get("id"),
                }
                return ToolResult(
                    success=output_data["success"],
                    output=json.dumps(output_data),
                    data=output_data,
                )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")