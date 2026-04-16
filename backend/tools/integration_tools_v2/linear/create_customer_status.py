from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class LinearCreateCustomerStatusTool(BaseTool):
    name = "linear_create_customer_status"
    description = "Create a new customer status in Linear"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="linear_access_token",
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
                    "description": "Customer status name",
                },
                "color": {
                    "type": "string",
                    "description": "Status color (hex code)",
                },
                "description": {
                    "type": "string",
                    "description": "Status description",
                },
                "displayName": {
                    "type": "string",
                    "description": "Display name for the status",
                },
                "position": {
                    "type": "number",
                    "description": "Position in status list",
                },
            },
            "required": ["name", "color"],
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
        
        input_dict: Dict[str, Any] = {
            "name": parameters["name"],
            "color": parameters["color"],
        }
        description = parameters.get("description")
        if description:
            input_dict["description"] = description
        display_name = parameters.get("displayName")
        if display_name:
            input_dict["displayName"] = display_name
        position = parameters.get("position")
        if position is not None:
            input_dict["position"] = position
        
        body = {
            "query": """
                mutation CustomerStatusCreate($input: CustomerStatusCreateInput!) {
                  customerStatusCreate(input: $input) {
                    success
                    status {
                      id
                      name
                      description
                      color
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
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code != 200:
                    return ToolResult(success=False, output="", error=response.text)
                
                try:
                    data = response.json()
                except Exception:
                    return ToolResult(success=False, output="", error="Invalid JSON response")
                
                if data.get("errors"):
                    error_msg = data["errors"][0].get("message", "Failed to create customer status") if data["errors"] else "Unknown GraphQL error"
                    return ToolResult(success=False, output="", error=error_msg)
                
                result = data.get("data", {}).get("customerStatusCreate", {})
                if not result.get("success"):
                    return ToolResult(success=False, output="", error="Customer status creation was not successful")
                
                status = result.get("status", {})
                output_data = {"customerStatus": status}
                return ToolResult(
                    success=True,
                    output=str(output_data),
                    data=output_data
                )
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")