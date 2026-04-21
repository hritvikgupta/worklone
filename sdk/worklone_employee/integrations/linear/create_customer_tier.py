from typing import Any, Dict
import httpx
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class LinearCreateCustomerTierTool(BaseTool):
    name = "linear_create_customer_tier"
    description = "Create a new customer tier in Linear"
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
                    "description": "Customer tier name",
                },
                "color": {
                    "type": "string",
                    "description": "Tier color (hex code)",
                },
                "displayName": {
                    "type": "string",
                    "description": "Display name for the tier",
                },
                "description": {
                    "type": "string",
                    "description": "Tier description",
                },
                "position": {
                    "type": "number",
                    "description": "Position in tier list",
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
        
        input_data: Dict[str, Any] = {
            "name": parameters["name"],
            "color": parameters["color"],
        }
        display_name = parameters.get("displayName")
        if display_name is not None and display_name != "":
            input_data["displayName"] = display_name
        description_val = parameters.get("description")
        if description_val is not None and description_val != "":
            input_data["description"] = description_val
        position = parameters.get("position")
        if position is not None:
            input_data["position"] = position
        
        body = {
            "query": """
mutation CustomerTierCreate($input: CustomerTierCreateInput!) {
  customerTierCreate(input: $input) {
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
                "input": input_data,
            },
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code not in [200, 201, 204]:
                    return ToolResult(success=False, output="", error=response.text)
                
                try:
                    data = response.json()
                except Exception:
                    return ToolResult(success=False, output="", error="Invalid JSON response")
                
                if data.get("errors"):
                    errors = data["errors"]
                    error_msg = (
                        errors[0].get("message", "Unknown GraphQL error")
                        if isinstance(errors, list) and errors
                        else "GraphQL errors"
                    )
                    return ToolResult(success=False, output="", error=error_msg)
                
                customer_tier_create = data.get("data", {}).get("customerTierCreate", {})
                if not isinstance(customer_tier_create, dict) or not customer_tier_create.get("success"):
                    return ToolResult(success=False, output="", error="Customer tier creation was not successful")
                
                customer_tier = customer_tier_create.get("customerTier")
                return ToolResult(
                    success=True,
                    output=response.text,
                    data={"customerTier": customer_tier},
                )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")