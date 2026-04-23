from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ShopifyDeleteProductTool(BaseTool):
    name = "shopify_delete_product"
    description = "Delete a product from your Shopify store"
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
                "productId": {
                    "type": "string",
                    "description": "Product ID to delete (gid://shopify/Product/123456789)",
                },
            },
            "required": ["shopDomain", "productId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": access_token,
        }
        
        shop_domain = parameters["shopDomain"]
        product_id = parameters["productId"]
        url = f"https://{shop_domain}/admin/api/2024-10/graphql.json"
        
        body = {
            "query": """
                mutation productDelete($input: ProductDeleteInput!) {
                  productDelete(input: $input) {
                    deletedProductId
                    userErrors {
                      field
                      message
                    }
                  }
                }
            """,
            "variables": {
                "input": {
                    "id": product_id,
                },
            },
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code not in [200]:
                    return ToolResult(success=False, output="", error=response.text)
                
                response_data = response.json()
                
                if "errors" in response_data and response_data["errors"]:
                    error_msg = response_data["errors"][0].get("message", "Failed to delete product")
                    return ToolResult(success=False, output="", error=error_msg)
                
                result = response_data.get("data", {}).get("productDelete")
                if not result:
                    return ToolResult(success=False, output="", error="Product deletion was not successful")
                
                user_errors = result.get("userErrors", [])
                if user_errors:
                    error_msgs = [e.get("message", "") for e in user_errors]
                    return ToolResult(success=False, output="", error=", ".join(error_msgs))
                
                deleted_id = result.get("deletedProductId")
                if not deleted_id:
                    return ToolResult(success=False, output="", error="Product deletion was not successful")
                
                return ToolResult(success=True, output={"deletedId": deleted_id}, data=response_data)
                
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")