from typing import Any, Dict
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ShopifyUpdateCustomerTool(BaseTool):
    name = "shopify_update_customer"
    description = "Update an existing customer in your Shopify store"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="SHOPIFY_ACCESS_TOKEN",
                description="Shopify access token",
                env_var="SHOPIFY_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "shopify",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("SHOPIFY_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "shopDomain": {
                    "type": "string",
                    "description": "Your Shopify store domain (e.g., mystore.myshopify.com)",
                },
                "customerId": {
                    "type": "string",
                    "description": "Customer ID to update (gid://shopify/Customer/123456789)",
                },
                "email": {
                    "type": "string",
                    "description": "New customer email address",
                },
                "firstName": {
                    "type": "string",
                    "description": "New customer first name",
                },
                "lastName": {
                    "type": "string",
                    "description": "New customer last name",
                },
                "phone": {
                    "type": "string",
                    "description": "New customer phone number",
                },
                "note": {
                    "type": "string",
                    "description": "New note about the customer",
                },
                "tags": {
                    "type": "array",
                    "description": "New customer tags",
                    "items": {
                        "type": "string",
                    },
                },
            },
            "required": ["shopDomain", "customerId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        shop_domain = parameters.get("shopDomain")
        if not shop_domain:
            return ToolResult(success=False, output="", error="shopDomain is required.")
        
        customer_id = parameters.get("customerId")
        if not customer_id:
            return ToolResult(success=False, output="", error="customerId is required.")
        
        url = f"https://{shop_domain}/admin/api/2024-10/graphql.json"
        
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": access_token,
        }
        
        input_data: dict = {"id": customer_id}
        for field in ["email", "firstName", "lastName", "phone", "note"]:
            if field in parameters:
                input_data[field] = parameters[field]
        if "tags" in parameters:
            input_data["tags"] = parameters["tags"]
        
        body = {
            "query": """
mutation customerUpdate($input: CustomerInput!) {
  customerUpdate(input: $input) {
    customer {
      id
      email
      firstName
      lastName
      phone
      createdAt
      updatedAt
      note
      tags
      amountSpent {
        amount
        currencyCode
      }
      addresses {
        address1
        city
        province
        country
        zip
      }
      defaultAddress {
        address1
        city
        province
        country
        zip
      }
    }
    userErrors {
      field
      message
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
                
                if response.status_code != 200:
                    return ToolResult(success=False, output="", error=f"HTTP {response.status_code}: {response.text}")
                
                data = response.json()
                
                if "errors" in data and data["errors"]:
                    error_msg = data["errors"][0].get("message", "Failed to update customer")
                    return ToolResult(success=False, output="", error=error_msg)
                
                result = data.get("data", {}).get("customerUpdate")
                if not result:
                    return ToolResult(success=False, output="", error="No customerUpdate result")
                
                user_errors = result.get("userErrors", [])
                if user_errors:
                    error_msgs = [ue.get("message", "") for ue in user_errors]
                    error_msg = ", ".join([msg for msg in error_msgs if msg])
                    return ToolResult(success=False, output="", error=error_msg)
                
                customer = result.get("customer")
                if not customer:
                    return ToolResult(success=False, output="", error="Customer update was not successful")
                
                return ToolResult(success=True, output=str(customer), data={"customer": customer})
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")