from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ShopifyListInventoryItemsTool(BaseTool):
    name = "shopify_list_inventory_items"
    description = "List inventory items from your Shopify store. Use this to find inventory item IDs by SKU."
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
                "first": {
                    "type": "number",
                    "description": "Number of inventory items to return (default: 50, max: 250)",
                },
                "query": {
                    "type": "string",
                    "description": 'Search query to filter inventory items (e.g., "sku:ABC123")',
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
        
        url = f"https://{shop_domain}/admin/api/2024-10/graphql.json"
        
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": access_token,
        }
        
        first = min(int(parameters.get("first", 50)), 250)
        variables = {
            "first": first,
            "query": parameters.get("query"),
        }
        body = {
            "query": """
query listInventoryItems($first: Int!, $query: String) {
  inventoryItems(first: $first, query: $query) {
    edges {
      node {
        id
        sku
        tracked
        createdAt
        updatedAt
        variant {
          id
          title
          product {
            id
            title
          }
        }
        inventoryLevels(first: 10) {
          edges {
            node {
              id
              quantities(names: ["available", "on_hand"]) {
                name
                quantity
              }
              location {
                id
                name
              }
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
            """,
            "variables": variables,
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code != 200:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                
        except json.JSONDecodeError:
            return ToolResult(success=False, output="", error="Invalid JSON response")
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
        
        if data.get("errors"):
            error_msg = data["errors"][0].get("message", "Failed to list inventory items") if data["errors"] else "Unknown GraphQL error"
            return ToolResult(success=False, output="", error=error_msg)
        
        inventory_items_data = data.get("data", {}).get("inventoryItems")
        if not inventory_items_data:
            return ToolResult(success=False, output="", error="Failed to retrieve inventory items")
        
        inventory_items = []
        for edge in inventory_items_data["edges"]:
            node = edge["node"]
            inv_levels_edges = node.get("inventoryLevels", {}).get("edges", [])
            inv_levels = []
            for level_edge in inv_levels_edges:
                level_node = level_edge["node"]
                quantities = level_node.get("quantities", [])
                available_qty = next((q["quantity"] for q in quantities if q["name"] == "available"), 0)
                inv_levels.append({
                    "id": level_node["id"],
                    "available": available_qty,
                    "location": level_node["location"],
                })
            item = {
                "id": node["id"],
                "sku": node["sku"],
                "tracked": node["tracked"],
                "createdAt": node["createdAt"],
                "updatedAt": node["updatedAt"],
                "variant": node.get("variant"),
                "inventoryLevels": inv_levels,
            }
            inventory_items.append(item)
        
        transformed = {
            "inventoryItems": inventory_items,
            "pageInfo": inventory_items_data["pageInfo"],
        }
        return ToolResult(success=True, output=json.dumps(transformed), data=transformed)