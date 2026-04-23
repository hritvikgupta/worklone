from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ShopifyAdjustInventoryTool(BaseTool):
    name = "Shopify Adjust Inventory"
    description = "Adjust inventory quantity for a product variant at a specific location"
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
                "inventoryItemId": {
                    "type": "string",
                    "description": "Inventory item ID (gid://shopify/InventoryItem/123456789)",
                },
                "locationId": {
                    "type": "string",
                    "description": "Location ID (gid://shopify/Location/123456789)",
                },
                "delta": {
                    "type": "number",
                    "description": "Amount to adjust (positive to increase, negative to decrease)",
                },
            },
            "required": ["shopDomain", "inventoryItemId", "locationId", "delta"],
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
        
        body = {
            "query": """
            mutation inventoryAdjustQuantities($input: InventoryAdjustQuantitiesInput!) {
              inventoryAdjustQuantities(input: $input) {
                inventoryAdjustmentGroup {
                  createdAt
                  reason
                  changes {
                    name
                    delta
                    quantityAfterChange
                    item {
                      id
                      sku
                    }
                    location {
                      id
                      name
                    }
                  }
                }
                userErrors {
                  field
                  message
                }
              }
            }
            """,
            "variables": {
                "input": {
                    "reason": "correction",
                    "name": "available",
                    "changes": [
                        {
                            "inventoryItemId": parameters["inventoryItemId"],
                            "locationId": parameters["locationId"],
                            "delta": parameters["delta"],
                        }
                    ],
                }
            },
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code not in [200]:
                    return ToolResult(success=False, output="", error=response.text)
                
                try:
                    data = response.json()
                except Exception:
                    return ToolResult(success=False, output="", error="Invalid JSON response")
                
                if data.get("errors"):
                    error_msg = data["errors"][0].get("message", "Failed to adjust inventory") if data["errors"] else "GraphQL errors"
                    return ToolResult(success=False, output="", error=error_msg)
                
                result = data.get("data", {}).get("inventoryAdjustQuantities", {})
                user_errors = result.get("userErrors", [])
                if user_errors:
                    error_msgs = [e.get("message", "") for e in user_errors]
                    return ToolResult(success=False, output="", error=", ".join(error_msgs))
                
                adjustment_group = result.get("inventoryAdjustmentGroup")
                if not adjustment_group:
                    return ToolResult(success=False, output="", error="Inventory adjustment was not successful")
                
                return ToolResult(success=True, output=response.text, data=data)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")