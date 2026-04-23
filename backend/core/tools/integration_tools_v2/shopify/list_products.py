from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ShopifyListProductsTool(BaseTool):
    name = "shopify_list_products"
    description = "List products from your Shopify store with optional filtering"
    category = "integration"

    GRAPHQL_QUERY = """
    query listProducts($first: Int!, $query: String) {
      products(first: $first, query: $query) {
        edges {
          node {
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
            variants(first: 10) {
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
            images(first: 5) {
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
        pageInfo {
          hasNextPage
          hasPreviousPage
        }
      }
    }
    """.strip()

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
                "first": {
                    "type": "number",
                    "description": "Number of products to return (default: 50, max: 250)",
                },
                "query": {
                    "type": "string",
                    "description": 'Search query to filter products (e.g., "title:shirt" or "vendor:Nike" or "status:active")',
                },
            },
            "required": ["shopDomain"],
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
        url = f"https://{shop_domain}/admin/api/2024-10/graphql.json"
        
        first = min(int(parameters.get("first", 50)), 250)
        query_str = parameters.get("query")
        variables = {
            "first": first,
            "query": query_str if query_str else None,
        }
        json_body = {
            "query": self.GRAPHQL_QUERY,
            "variables": variables,
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=json_body)
                
                if response.status_code != 200:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                
                if "errors" in data and data["errors"]:
                    error_msg = data["errors"][0].get("message", "Failed to list products")
                    return ToolResult(success=False, output="", error=error_msg)
                
                products_data = data.get("data", {}).get("products")
                if not products_data:
                    return ToolResult(success=False, output="", error="Failed to retrieve products")
                
                products = [edge["node"] for edge in products_data["edges"]]
                page_info = products_data.get("pageInfo", {})
                output_data = {
                    "products": products,
                    "pageInfo": page_info,
                }
                
                return ToolResult(success=True, output=response.text, data=output_data)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")