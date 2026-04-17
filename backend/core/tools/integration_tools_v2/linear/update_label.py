from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class LinearUpdateLabelTool(BaseTool):
    name = "linear_update_label"
    description = "Update an existing label in Linear"
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

    def _build_body(self, parameters: dict) -> dict:
        input_data: dict[str, Any] = {}
        name = parameters.get("name")
        if name is not None and name != "":
            input_data["name"] = name
        color = parameters.get("color")
        if color is not None and color != "":
            input_data["color"] = color
        description = parameters.get("description")
        if description is not None and description != "":
            input_data["description"] = description
        return {
            "query": """
            mutation UpdateLabel($id: String!, $input: IssueLabelUpdateInput!) {
              issueLabelUpdate(id: $id, input: $input) {
                success
                issueLabel {
                  id
                  name
                  color
                  description
                  isGroup
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
                "id": parameters["labelId"],
                "input": input_data,
            },
        }

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "labelId": {
                    "type": "string",
                    "description": "Label ID to update",
                },
                "name": {
                    "type": "string",
                    "description": "New label name",
                },
                "color": {
                    "type": "string",
                    "description": "New label color (hex format)",
                },
                "description": {
                    "type": "string",
                    "description": "New label description",
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
        
        url = "https://api.linear.app/graphql"
        json_body = self._build_body(parameters)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=json_body)
                
                if response.status_code != 200:
                    return ToolResult(success=False, output="", error=response.text)
                
                try:
                    parsed = response.json()
                except Exception:
                    return ToolResult(success=False, output="", error="Invalid JSON response")
                
                if "errors" in parsed and parsed["errors"]:
                    error_msg = parsed["errors"][0].get("message", "Failed to update label")
                    return ToolResult(success=False, output="", error=error_msg)
                
                if "data" not in parsed or "issueLabelUpdate" not in parsed["data"]:
                    return ToolResult(success=False, output="", error="Invalid response structure")
                
                result = parsed["data"]["issueLabelUpdate"]
                if not result.get("success"):
                    return ToolResult(success=False, output="", error="Label update was not successful")
                
                return ToolResult(success=True, output=response.text, data=parsed)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")