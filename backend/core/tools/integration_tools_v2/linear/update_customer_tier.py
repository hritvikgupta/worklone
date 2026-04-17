from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class LinearUpdateCustomerTierTool(BaseTool):
    name = "linear_update_customer_tier"
    description = "Update a customer tier in Linear"
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
                "tierId": {
                    "type": "string",
                    "description": "Customer tier ID to update",
                },
                "name": {
                    "type": "string",
                    "description": "Updated tier name",
                },
                "color": {
                    "type": "string",
                    "description": "Updated tier color",
                },
                "displayName": {
                    "type": "string",
                    "description": "Updated display name",
                },
                "description": {
                    "type": "string",
                    "description": "Updated description",
                },
                "position": {
                    "type": "number",
                    "description": "Updated position",
                },
            },
            "required": ["tierId"],
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
        display_name = parameters.get("displayName")
        if display_name is not None and display_name != "":
            input_data["displayName"] = display_name
        description = parameters.get("description")
        if description is not None and description != "":
            input_data["description"] = description
        position = parameters.get("position")
        if position is not None:
            input_data["position"] = position
        
        tier_id = parameters["tierId"]
        
        body = {
            "query": """
mutation CustomerTierUpdate($id: String!, $input: CustomerTierUpdateInput!) {
  customerTierUpdate(id: $id, input: $input) {
    success
    customerTier {
      id
      name
      displayName
      description
      color
      position
      createdAt
      archivedAt
    }
  }
}
            """,
            "variables": {
                "id": tier_id,
                "input": input_data,
            },
        }
        
        url = "https://api.linear.app/graphql"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code != 200:
                    return ToolResult(success=False, output="", error=f"HTTP {response.status_code}: {response.text}")
                
                try:
                    data = response.json()
                except Exception:
                    return ToolResult(success=False, output="", error="Invalid JSON response")
                
                if "errors" in data and data["errors"]:
                    error_msg = data["errors"][0].get("message", "Failed to update customer tier")
                    return ToolResult(success=False, output="", error=error_msg)
                
                result = data.get("data", {}).get("customerTierUpdate", {})
                if not result.get("success"):
                    return ToolResult(success=False, output="", error="Failed to update customer tier")
                
                customer_tier = result.get("customerTier", {})
                output_data = {"customerTier": customer_tier}
                return ToolResult(success=True, output=str(output_data), data=output_data)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")