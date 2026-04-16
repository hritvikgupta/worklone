from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class LinearUpdateCustomerStatusTool(BaseTool):
    name = "linear_update_customer_status"
    description = "Update a customer status in Linear"
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
                "statusId": {
                    "type": "string",
                    "description": "Customer status ID to update",
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
                "displayName": {
                    "type": "string",
                    "description": "Updated display name",
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
        display_name = parameters.get("displayName")
        if display_name is not None and display_name != "":
            input_data["displayName"] = display_name
        position = parameters.get("position")
        if position is not None:
            input_data["position"] = position
        
        status_id = parameters["statusId"]
        
        json_body = {
            "query": """
            mutation CustomerStatusUpdate($id: String!, $input: CustomerStatusUpdateInput!) {
              customerStatusUpdate(id: $id, input: $input) {
                success
                customerStatus {
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
                "id": status_id,
                "input": input_data,
            },
        }
        
        url = "https://api.linear.app/graphql"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=json_body)
                
                if response.status_code not in [200, 201]:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                
                if "errors" in data and data["errors"]:
                    error_msg = data["errors"][0].get("message", "Failed to update customer status")
                    return ToolResult(success=False, output="", error=error_msg)
                
                result = data.get("data", {}).get("customerStatusUpdate", {})
                if not result.get("success", False):
                    return ToolResult(success=False, output="", error="Failed to update customer status")
                
                customer_status = result.get("customerStatus", {})
                return ToolResult(success=True, output=str(customer_status), data=customer_status)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")