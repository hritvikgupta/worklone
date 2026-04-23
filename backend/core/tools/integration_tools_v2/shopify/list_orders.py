from typing import Any, Dict
import httpx
from textwrap import dedent
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ShopifyListOrdersTool(BaseTool):
    name = "shopify_list_orders"
    description = "List orders from your Shopify store with optional filtering"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="shopify_access_token",
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
            context_token_keys=("shopify_access_token",),
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
                    "description": "Number of orders to return (default: 50, max: 250)",
                },
                "status": {
                    "type": "string",
                    "description": "Filter by order status (open, closed, cancelled, any)",
                },
                "query": {
                    "type": "string",
                    "description": 'Search query to filter orders (e.g., "financial_status:paid" or "fulfillment_status:unfulfilled" or "email:customer@example.com")',
                },
            },
            "required": ["shopDomain"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        shop_domain = parameters["shopDomain"]
        url = f"https://{shop_domain}/admin/api/2024-10/graphql.json"

        first = min(parameters.get("first", 50), 250)
        status = parameters.get("status")
        query_input = parameters.get("query")
        query_parts: list[str] = []
        if status and status != "any":
            query_parts.append(f"status:{status}")
        if query_input:
            query_parts.append(query_input)
        query_string = " ".join(query_parts) if query_parts else None

        variables = {
            "first": first,
            "query": query_string,
        }

        graphql_query = dedent("""
            query listOrders($first: Int!, $query: String) {
              orders(first: $first, query: $query) {
                edges {
                  node {
                    id
                    name
                    email
                    phone
                    createdAt
                    updatedAt
                    cancelledAt
                    closedAt
                    displayFinancialStatus
                    displayFulfillmentStatus
                    totalPriceSet {
                      shopMoney {
                        amount
                        currencyCode
                      }
                    }
                    subtotalPriceSet {
                      shopMoney {
                        amount
                        currencyCode
                      }
                    }
                    note
                    tags
                    customer {
                      id
                      email
                      firstName
                      lastName
                    }
                    lineItems(first: 10) {
                      edges {
                        node {
                          id
                          title
                          quantity
                          variant {
                            id
                            title
                            price
                            sku
                          }
                        }
                      }
                    }
                    shippingAddress {
                      firstName
                      lastName
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
        """).strip()

        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": access_token,
        }
        body = {
            "query": graphql_query,
            "variables": variables,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code not in [200, 201, 204]:
                    return ToolResult(success=False, output="", error=response.text)

                response_data = response.json()

                if response_data.get("errors"):
                    errors = response_data["errors"]
                    error_msg = errors[0].get("message", "Failed to list orders") if errors else "Unknown GraphQL error"
                    return ToolResult(success=False, output="", error=error_msg)

                data = response_data.get("data", {})
                orders_data = data.get("orders")
                if not orders_data:
                    return ToolResult(success=False, output="", error="Failed to retrieve orders")

                orders = [edge["node"] for edge in orders_data["edges"]]
                transformed = {
                    "orders": orders,
                    "pageInfo": orders_data["pageInfo"],
                }

                return ToolResult(success=True, output=response.text, data=transformed)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")