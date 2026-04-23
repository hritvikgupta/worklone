from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ShopifyCreateFulfillmentTool(BaseTool):
    name = "shopify_create_fulfillment"
    description = "Create a fulfillment to mark order items as shipped. Requires a fulfillment order ID (get this from the order details)."
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
                "fulfillmentOrderId": {
                    "type": "string",
                    "description": "The fulfillment order ID (e.g., gid://shopify/FulfillmentOrder/123456789)",
                },
                "trackingNumber": {
                    "type": "string",
                    "description": "Tracking number for the shipment",
                },
                "trackingCompany": {
                    "type": "string",
                    "description": "Shipping carrier name (e.g., UPS, FedEx, USPS, DHL)",
                },
                "trackingUrl": {
                    "type": "string",
                    "description": "URL to track the shipment",
                },
                "notifyCustomer": {
                    "type": "boolean",
                    "description": "Whether to send a shipping confirmation email to the customer (default: true)",
                },
            },
            "required": ["shopDomain", "fulfillmentOrderId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        shop_domain = parameters["shopDomain"]
        fulfillment_order_id = parameters["fulfillmentOrderId"]
        tracking_number = parameters.get("trackingNumber")
        tracking_company = parameters.get("trackingCompany")
        tracking_url = parameters.get("trackingUrl")
        notify_customer = parameters.get("notifyCustomer", True) != False

        tracking_info: Dict[str, str] = {}
        if tracking_number:
            tracking_info["number"] = tracking_number
        if tracking_company:
            tracking_info["company"] = tracking_company
        if tracking_url:
            tracking_info["url"] = tracking_url

        fulfillment_input: Dict[str, Any] = {
            "lineItemsByFulfillmentOrder": [
                {
                    "fulfillmentOrderId": fulfillment_order_id,
                },
            ],
            "notifyCustomer": notify_customer,
        }
        if tracking_info:
            fulfillment_input["trackingInfo"] = tracking_info

        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": access_token,
        }
        
        url = f"https://{shop_domain}/admin/api/2024-10/graphql.json"
        
        query = """
          mutation fulfillmentCreateV2($fulfillment: FulfillmentV2Input!) {
            fulfillmentCreateV2(fulfillment: $fulfillment) {
              fulfillment {
                id
                status
                createdAt
                updatedAt
                trackingInfo {
                  company
                  number
                  url
                }
                fulfillmentLineItems(first: 50) {
                  edges {
                    node {
                      id
                      quantity
                      lineItem {
                        title
                      }
                    }
                  }
                }
              }
              userErrors {
                field
                message
              }
            }
          }
        """
        body = {
            "query": query,
            "variables": {
                "fulfillment": fulfillment_input,
            },
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code not in [200, 201, 204]:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                
                if "errors" in data and data["errors"]:
                    error = data["errors"][0].get("message", "Failed to create fulfillment")
                    return ToolResult(success=False, output="", error=error)
                
                result = data.get("data", {}).get("fulfillmentCreateV2")
                if not result:
                    return ToolResult(success=False, output="", error="Failed to create fulfillment")
                
                user_errors = result.get("userErrors", [])
                if user_errors:
                    error_msgs = [e.get("message", "") for e in user_errors if e.get("message")]
                    return ToolResult(success=False, output="", error=", ".join(error_msgs))
                
                fulfillment = result.get("fulfillment")
                if not fulfillment:
                    return ToolResult(success=False, output="", error="No fulfillment returned")
                
                fulfillment_line_items_edges = fulfillment.get("fulfillmentLineItems", {}).get("edges", [])
                fulfillment_line_items = [edge["node"] for edge in fulfillment_line_items_edges]
                
                transformed = {
                    "fulfillment": {
                        "id": fulfillment["id"],
                        "status": fulfillment["status"],
                        "createdAt": fulfillment["createdAt"],
                        "updatedAt": fulfillment["updatedAt"],
                        "trackingInfo": fulfillment.get("trackingInfo", []),
                        "fulfillmentLineItems": fulfillment_line_items,
                    }
                }
                return ToolResult(success=True, output=json.dumps(transformed), data=transformed)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")