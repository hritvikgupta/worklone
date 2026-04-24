from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ShopifyCancelOrderTool(BaseTool):
    name = "shopify_cancel_order"
    description = "Cancel an order in your Shopify store"
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
                "orderId": {
                    "type": "string",
                    "description": "Order ID to cancel (gid://shopify/Order/123456789)",
                },
                "reason": {
                    "type": "string",
                    "description": "Cancellation reason (CUSTOMER, DECLINED, FRAUD, INVENTORY, STAFF, OTHER)",
                },
                "notifyCustomer": {
                    "type": "boolean",
                    "description": "Whether to notify the customer about the cancellation",
                },
                "refund": {
                    "type": "boolean",
                    "description": "Whether to refund the order",
                },
                "restock": {
                    "type": "boolean",
                    "description": "Whether to restock the inventory",
                },
                "staffNote": {
                    "type": "string",
                    "description": "A note about the cancellation for staff reference",
                },
            },
            "required": ["shopDomain", "orderId", "reason"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": access_token,
        }

        shop_domain = parameters.get("shopDomain")
        if not shop_domain:
            return ToolResult(success=False, output="", error="shopDomain is required.")

        url = f"https://{shop_domain}/admin/api/2024-10/graphql.json"

        body = {
            "query": """
            mutation orderCancel($orderId: ID!, $reason: OrderCancelReason!, $notifyCustomer: Boolean, $refund: Boolean!, $restock: Boolean!, $staffNote: String) {
              orderCancel(orderId: $orderId, reason: $reason, notifyCustomer: $notifyCustomer, refund: $refund, restock: $restock, staffNote: $staffNote) {
                job {
                  id
                  done
                }
                orderCancelUserErrors {
                  field
                  message
                  code
                }
              }
            }
            """,
            "variables": {
                "orderId": parameters["orderId"],
                "reason": parameters["reason"],
                "notifyCustomer": parameters.get("notifyCustomer", False),
                "refund": parameters.get("refund", False),
                "restock": parameters.get("restock", False),
                "staffNote": parameters.get("staffNote") or None,
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

                if "errors" in data and data["errors"]:
                    return ToolResult(
                        success=False,
                        output="",
                        error=data["errors"][0].get("message", "Failed to cancel order"),
                    )

                result = data.get("data", {}).get("orderCancel", {})
                user_errors = result.get("orderCancelUserErrors", [])
                if user_errors:
                    error_msg = ", ".join(e.get("message", "") for e in user_errors)
                    return ToolResult(success=False, output="", error=error_msg)

                output_data = {
                    "order": {
                        "id": result.get("job", {}).get("id"),
                        "cancelled": result.get("job", {}).get("done", True),
                        "message": "Order cancellation initiated",
                    }
                }
                return ToolResult(success=True, output=str(output_data), data=output_data)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")