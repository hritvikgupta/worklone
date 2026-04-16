from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class LinearCreateLabelTool(BaseTool):
    name = "linear_create_label"
    description = "Create a new label in Linear"
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
                    "description": "Label name",
                },
                "color": {
                    "type": "string",
                    "description": "Label color (hex format, e.g., \"#ff0000\")",
                },
                "description": {
                    "type": "string",
                    "description": "Label description",
                },
                "teamId": {
                    "type": "string",
                    "description": "Team ID (if omitted, creates workspace label)",
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
        for field in ["color", "description", "teamId"]:
            val = parameters.get(field)
            if val is not None and str(val).strip() != "":
                input_data[field] = val
        
        body = {
            "query": """
            mutation CreateLabel($input: IssueLabelCreateInput!) {
              issueLabelCreate(input: $input) {
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
            """.strip(),
            "variables": {
                "input": input_data,
            },
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code not in [200, 201]:
                    return ToolResult(
                        success=False, output="", error=f"HTTP {response.status_code}: {response.text}"
                    )
                
                data = response.json()
                
                if "errors" in data and data["errors"]:
                    error_msg = data["errors"][0].get("message", "Failed to create label")
                    return ToolResult(success=False, output="", error=error_msg)
                
                result = data.get("data", {}).get("issueLabelCreate", {})
                if not result.get("success", False):
                    return ToolResult(
                        success=False, output="", error="Label creation was not successful"
                    )
                
                label = result.get("issueLabel", {})
                output_data = {"label": label}
                return ToolResult(
                    success=True, output=str(output_data), data=output_data
                )
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")