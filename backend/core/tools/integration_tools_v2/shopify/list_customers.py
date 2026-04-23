from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ShopifyListCustomersTool(BaseTool):
    name = "shopify_list_customers"
    description = "List customers from your Shopify store with optional filtering"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="SHOPIFY_ACCESS_TOKEN",
                description="Access token for your Shopify store",
                env_var="SHOPIFY_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "shopify",
            context=context,
            context_token_keys=("shopify_token",),
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
                    "description": "Number of customers to return (default: 50, max: 250)",
                },
                "query": {
                    "type": "string",
                    "description": 'Search query to filter customers (e.g., "first_name:John" or "last_name:Smith" or "email:*@gmail.com" or "tag:vip")',
                },
            },
            "required": ["shopDomain"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        shop_domain = parameters["shopDomain"]
        first = min(int(parameters.get("first", 50)), 250)
        query_param = parameters.get("query")
        query = query_param if query_param else None
        
        url = f"https://{shop_domain}/admin/api/2024-10/graphql.json"
        
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": access_token,
        }
        
        body = {
            "query": """
            query listCustomers($first: Int!, $query: String) {
              customers(first: $first, query: $query) {
                edges {
                  node {
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
                    defaultAddress {
                      address1
                      city
                      province
                      country
                      zip
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
                "query": query,
            },
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code not in [200, 201, 204]:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                
                if data.get("errors"):
                    error_msg = data["errors"][0].get("message", "Failed to list customers") if data["errors"] else "Failed to list customers"
                    return ToolResult(success=False, output="", error=error_msg)
                
                customers_data = data.get("data", {}).get("customers")
                if not customers_data:
                    return ToolResult(success=False, output="", error="Failed to retrieve customers")
                
                customers = [edge["node"] for edge in customers_data["edges"]]
                
                output_data = {
                    "customers": customers,
                    "pageInfo": customers_data["pageInfo"],
                }
                
                return ToolResult(success=True, output=response.text, data=output_data)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")