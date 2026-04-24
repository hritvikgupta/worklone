from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ShopifyGetProductTool(BaseTool):
    name = "shopify_get_product"
    description = "Get a single product by ID from your Shopify store"
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
                    "description": "Product ID (gid://shopify/Product/123456789)",
                },
            },
            "required": ["shopDomain", "productId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        shop_domain = parameters["shopDomain"]
        product_id = parameters["productId"]
        
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": access_token,
        }
        
        url = f"https://{shop_domain}/admin/api/2024-10/graphql.json"
        
        body = {
            "query": """
              query getProduct($id: ID!) {
                product(id: $id) {
                  id
                  title
                  handle
                  descriptionHtml
                  vendor
                  productType
                  tags
                  status
                  createdAt
                  updatedAt
                  variants(first: 50) {
                    edges {
                      node {
                        id
                        title
                        price
                        compareAtPrice
                        sku
                        inventoryQuantity
                      }
                    }
                  }
                  images(first: 20) {
                    edges {
                      node {
                        id
                        url
                        altText
                      }
                    }
                  }
                }
              }
            """,
            "variables": {
                "id": product_id,
            },
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code not in [200, 201, 204]:
                    return ToolResult(success=False, output="", error=response.text)
                
                try:
                    response_json = response.json()
                except Exception as parse_error:
                    return ToolResult(success=False, output="", error=f"Invalid JSON response: {str(parse_error)}")
                
                if response_json.get("errors"):
                    errors = response_json["errors"]
                    error_msg = errors[0].get("message", "Failed to get product") if errors else "GraphQL errors occurred"
                    return ToolResult(success=False, output="", error=error_msg)
                
                product = response_json.get("data", {}).get("product")
                if not product:
                    return ToolResult(success=False, output="", error="Product not found")
                
                processed_data = {"product": product}
                return ToolResult(
                    success=True,
                    output=json.dumps(processed_data),
                    data=processed_data
                )
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")