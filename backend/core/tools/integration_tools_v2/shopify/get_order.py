from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ShopifyGetOrderTool(BaseTool):
    name = "shopify_get_order"
    description = "Get a single order by ID from your Shopify store"
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
                "orderId": {
                    "type": "string",
                    "description": "Order ID (gid://shopify/Order/123456789)",
                },
            },
            "required": ["shopDomain", "orderId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        shop_domain = parameters.get("shopDomain")
        if not shop_domain:
            return ToolResult(success=False, output="", error="shopDomain is required.")
        
        order_id = parameters.get("orderId")
        if not order_id:
            return ToolResult(success=False, output="", error="orderId is required.")
        
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": access_token,
        }
        
        url = f"https://{shop_domain}/admin/api/2024-10/graphql.json"
        
        query = """
        query getOrder($id: ID!) {
          order(id: $id) {
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
            totalTaxSet {
              shopMoney {
                amount
                currencyCode
              }
            }
            totalShippingPriceSet {
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
              phone
            }
            lineItems(first: 50) {
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
                  originalTotalSet {
                    shopMoney {
                      amount
                      currencyCode
                    }
                  }
                  discountedTotalSet {
                    shopMoney {
                      amount
                      currencyCode
                    }
                  }
                }
              }
            }
            shippingAddress {
              firstName
              lastName
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
            billingAddress {
              firstName
              lastName
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
            fulfillments {
              id
              status
              createdAt
              updatedAt
              trackingInfo {
                company
                number
                url
              }
            }
          }
        }
        """
        
        body = {
            "query": query.strip(),
            "variables": {
                "id": order_id,
            },
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code != 200:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"HTTP {response.status_code}: {response.text}",
                    )
                
                try:
                    data = response.json()
                except Exception as parse_e:
                    return ToolResult(
                        success=False,
                        output=response.text,
                        error=f"Failed to parse JSON response: {str(parse_e)}",
                    )
                
                errors = data.get("errors")
                if errors:
                    error_msg = (
                        errors[0].get("message", "GraphQL errors")
                        if isinstance(errors, list) and len(errors) > 0
                        else "GraphQL error"
                    )
                    return ToolResult(success=False, output="", error=error_msg)
                
                order = data.get("data", {}).get("order")
                if not order:
                    return ToolResult(success=False, output="", error="Order not found")
                
                return ToolResult(
                    success=True,
                    output=str(order),
                    data={"order": order},
                )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")