from typing import Any, Dict
import httpx
import textwrap
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ShopifyDeleteCustomerTool(BaseTool):
    name = "shopify_delete_customer"
    description = "Delete a customer from your Shopify store"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="SHOPIFY_ACCESS_TOKEN",
                description="Access token",
                env_var="SHOPIFY_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "shopify",
            context=context,
            context_token_keys=("provider_token",),
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
                    "description": "Customer ID to delete (gid://shopify/Customer/123456789)",
                },
            },
            "required": ["shopDomain", "customerId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        shop_domain = parameters.get("shopDomain")
        customer_id = parameters.get("customerId")
        
        if not shop_domain or not customer_id:
            return ToolResult(success=False, output="", error="Missing required parameters: shopDomain or customerId.")
        
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": access_token,
        }
        
        url = f"https://{shop_domain}/admin/api/2024-10/graphql.json"
        
        query = textwrap.dedent("""
            mutation customerDelete($input: CustomerDeleteInput!) {
              customerDelete(input: $input) {
                deletedCustomerId
                userErrors {
                  field
                  message
                }
              }
            }
        """).strip()
        
        body = {
            "query": query,
            "variables": {
                "input": {
                    "id": customer_id,
                },
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
                    return ToolResult(success=False, output=response.text, error="Invalid JSON response")
                
                if data.get("errors"):
                    errors = data["errors"]
                    error_msg = errors[0].get("message") if errors else "Failed to delete customer"
                    return ToolResult(success=False, output="", error=error_msg)
                
                result = data.get("data", {}).get("customerDelete", {})
                user_errors = result.get("userErrors", [])
                
                if user_errors:
                    error_msgs = [ue.get("message", "") for ue in user_errors if ue.get("message")]
                    return ToolResult(success=False, output="", error=", ".join(error_msgs))
                
                deleted_id = result.get("deletedCustomerId")
                if not deleted_id:
                    return ToolResult(success=False, output="", error="Customer deletion was not successful")
                
                output_data = {"deletedId": deleted_id}
                return ToolResult(
                    success=True,
                    output=str(output_data),
                    data=output_data
                )
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")