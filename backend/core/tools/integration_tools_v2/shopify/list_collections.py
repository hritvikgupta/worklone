from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ShopifyListCollectionsTool(BaseTool):
    name = "shopify_list_collections"
    description = "List product collections from your Shopify store. Filter by title, type (custom/smart), or handle."
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
                "first": {
                    "type": "number",
                    "description": "Number of collections to return (default: 50, max: 250)",
                },
                "query": {
                    "type": "string",
                    "description": 'Search query to filter collections (e.g., "title:Summer" or "collection_type:smart")',
                },
            },
            "required": ["shopDomain"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        shop_domain = parameters.get("shopDomain")
        if not shop_domain:
            return ToolResult(success=False, output="", error="shopDomain is required.")
        
        first = min(int(parameters.get("first", 50)), 250)
        query_param = parameters.get("query")
        
        variables = {
            "first": first,
            "query": query_param,
        }
        
        body = {
            "query": """
            query listCollections($first: Int!, $query: String) {
              collections(first: $first, query: $query) {
                edges {
                  node {
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
                  }
                }
                pageInfo {
                  hasNextPage
                  hasPreviousPage
                }
              }
            }
            """,
            "variables": variables,
        }
        
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": access_token,
        }
        
        url = f"https://{shop_domain}/admin/api/2024-10/graphql.json"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code != 200:
                    return ToolResult(success=False, output="", error=f"HTTP {response.status_code}: {response.text}")
                
                try:
                    data = response.json()
                except Exception:
                    return ToolResult(success=False, output=response.text, error="Invalid JSON response")
                
                if isinstance(data, dict) and "errors" in data and data["errors"]:
                    errors = data["errors"]
                    error_msg = errors[0].get("message", "GraphQL errors") if isinstance(errors, list) and errors else "GraphQL errors"
                    return ToolResult(success=False, output="", error=error_msg)
                
                collections_data = data.get("data", {}).get("collections")
                if not isinstance(collections_data, dict):
                    return ToolResult(success=False, output="", error="Failed to retrieve collections")
                
                edges = collections_data.get("edges", [])
                collections = []
                for edge in edges:
                    if not isinstance(edge, dict) or "node" not in edge:
                        continue
                    node = edge["node"]
                    if not isinstance(node, dict):
                        continue
                    collection = {
                        "id": node.get("id", ""),
                        "title": node.get("title", ""),
                        "handle": node.get("handle", ""),
                        "description": node.get("description"),
                        "descriptionHtml": node.get("descriptionHtml"),
                        "productsCount": node.get("productsCount", {}).get("count", 0),
                        "sortOrder": node.get("sortOrder", ""),
                        "updatedAt": node.get("updatedAt", ""),
                        "image": node.get("image"),
                    }
                    collections.append(collection)
                
                page_info = collections_data.get("pageInfo", {})
                output_data = {
                    "collections": collections,
                    "pageInfo": page_info,
                }
                output_str = json.dumps(output_data)
                return ToolResult(success=True, output=output_str, data=output_data)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")