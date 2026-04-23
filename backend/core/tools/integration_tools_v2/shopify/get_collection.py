from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ShopifyGetCollectionTool(BaseTool):
    name = "shopify_get_collection"
    description = "Get a specific collection by ID, including its products. Use this to retrieve products within a collection."
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
                "collectionId": {
                    "type": "string",
                    "description": "The collection ID (e.g., gid://shopify/Collection/123456789)",
                },
                "productsFirst": {
                    "type": "number",
                    "description": "Number of products to return from this collection (default: 50, max: 250)",
                },
            },
            "required": ["shopDomain", "collectionId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        shop_domain = parameters.get("shopDomain")
        if not shop_domain:
            return ToolResult(success=False, output="", error="shopDomain is required.")
        
        collection_id = parameters.get("collectionId")
        if not collection_id:
            return ToolResult(success=False, output="", error="collectionId is required.")
        
        products_first = min(parameters.get("productsFirst", 50), 250)
        
        url = f"https://{shop_domain}/admin/api/2024-10/graphql.json"
        
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": access_token,
        }
        
        query = """
        query getCollection($id: ID!, $productsFirst: Int!) {
          collection(id: $id) {
            id
            title
            handle
            description
            descriptionHtml
            productsCount {
              count
            }
            sortOrder
            updatedAt
            image {
              url
              altText
            }
            products(first: $productsFirst) {
              edges {
                node {
                  id
                  title
                  handle
                  status
                  vendor
                  productType
                  totalInventory
                  featuredMedia {
                    preview {
                      image {
                        url
                        altText
                      }
                    }
                  }
                }
              }
            }
          }
        }
        """
        
        body = {
            "query": query,
            "variables": {
                "id": collection_id,
                "productsFirst": products_first,
            },
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code not in [200, 201, 204]:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                
                if data.get("errors"):
                    errors = data["errors"]
                    error_msg = errors[0].get("message", "Failed to get collection") if errors else "Failed to get collection"
                    return ToolResult(success=False, output="", error=error_msg)
                
                collection = data.get("data", {}).get("collection")
                if not collection:
                    return ToolResult(success=False, output="", error="Collection not found")
                
                products = []
                edges = collection.get("products", {}).get("edges", [])
                for edge in edges:
                    node = edge.get("node", {})
                    featured_media = node.get("featuredMedia", {})
                    featured_image = featured_media.get("preview", {}).get("image") if featured_media.get("preview") else None
                    product = {
                        "id": node.get("id"),
                        "title": node.get("title"),
                        "handle": node.get("handle"),
                        "status": node.get("status"),
                        "vendor": node.get("vendor"),
                        "productType": node.get("productType"),
                        "totalInventory": node.get("totalInventory"),
                        "featuredImage": featured_image,
                    }
                    products.append(product)
                
                output_data = {
                    "collection": {
                        "id": collection.get("id"),
                        "title": collection.get("title"),
                        "handle": collection.get("handle"),
                        "description": collection.get("description"),
                        "descriptionHtml": collection.get("descriptionHtml"),
                        "productsCount": collection.get("productsCount", {}).get("count", 0),
                        "sortOrder": collection.get("sortOrder"),
                        "updatedAt": collection.get("updatedAt"),
                        "image": collection.get("image"),
                        "products": products,
                    }
                }
                
                return ToolResult(
                    success=True,
                    output=json.dumps(output_data),
                    data=output_data
                )
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")