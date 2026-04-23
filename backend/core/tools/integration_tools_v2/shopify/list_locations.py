from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ShopifyListLocationsTool(BaseTool):
    name = "shopify_list_locations"
    description = "List inventory locations from your Shopify store. Use this to find location IDs needed for inventory operations."
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
                    "description": "Number of locations to return (default: 50, max: 250)",
                },
                "includeInactive": {
                    "type": "boolean",
                    "description": "Whether to include deactivated locations (default: false)",
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
        first = min(parameters.get("first", 50), 250)
        include_inactive = parameters.get("includeInactive", False)
        
        url = f"https://{shop_domain}/admin/api/2024-10/graphql.json"
        
        body = {
            "query": """
                query listLocations($first: Int!, $includeInactive: Boolean) {
                  locations(first: $first, includeInactive: $includeInactive) {
                    edges {
                      node {
                        id
                        name
                        isActive
                        fulfillsOnlineOrders
                        address {
                          address1
                          address2
                          city
                          province
                          provinceCode
                          country
                          countryCode
                          zip
                          phone
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
            "variables": {
                "first": first,
                "includeInactive": include_inactive,
            },
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code != 200:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                
                if "errors" in data and data["errors"]:
                    error_msg = data["errors"][0].get("message", "Failed to list locations")
                    return ToolResult(success=False, output="", error=error_msg)
                
                locations_data = data.get("data", {}).get("locations")
                if not locations_data:
                    return ToolResult(success=False, output="", error="Failed to retrieve locations")
                
                locations = [edge["node"] for edge in locations_data.get("edges", [])]
                page_info = locations_data.get("pageInfo", {})
                
                output_data = {
                    "locations": locations,
                    "pageInfo": page_info,
                }
                
                return ToolResult(success=True, output=str(output_data), data=output_data)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")