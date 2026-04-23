from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ShopifyUpdateOrderTool(BaseTool):
    name = "shopify_update_order"
    description = "Update an existing order in your Shopify store (note, tags, email)"
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
            context_token_keys=("shopify_token",},
            env_token_keys=("SHOPIFY_ACCESS_TOKEN",},
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
                    "description": "Order ID to update (gid://shopify/Order/123456789)",
                },
                "note": {
                    "type": "string",
                    "description": "New order note",
                },
                "tags": {
                    "type": "array",
                    "description": "New order tags",
                    "items": {
                        "type": "string",
                    },
                },
                "email": {
                    "type": "string",
                    "description": "New customer email for the order",
                },
            },
            "required": ["shopDomain", "orderId"],
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

        input_dict: Dict[str, Any] = {
            "id": parameters["orderId"],
        }
        if "note" in parameters:
            input_dict["note"] = parameters["note"]
        if "tags" in parameters:
            input_dict["tags"] = parameters["tags"]
        if "email" in parameters:
            input_dict["email"] = parameters["email"]

        json_body = {
            "query": """
                mutation orderUpdate($input: OrderInput!) {
                  orderUpdate(input: $input) {
                    order {
                      id
                      name
                      email
                      phone
                      createdAt
                      updatedAt
                      note
                      tags
                      displayFinancialStatus
                      displayFulfillmentStatus
                      totalPriceSet {
                        shopMoney {
                          amount
                          currencyCode
                        }
                      }
                      customer {
                        id
                        email
                        firstName
                        lastName
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
                "input": input_dict,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=json_body)

                if response.status_code >= 400:
                    return ToolResult(success=False, output="", error=response.text)

                try:
                    data = response.json()
                except Exception:
                    return ToolResult(success=False, output=response.text, error="Invalid JSON response")

                if data.get("errors"):
                    errors = data["errors"]
                    error_msg = errors[0].get("message", "Failed to update order") if isinstance(errors, list) and errors else "GraphQL errors"
                    return ToolResult(success=False, output="", error=error_msg)

                result = data.get("data", {}).get("orderUpdate", {})
                user_errors = result.get("userErrors", [])
                if user_errors:
                    error_msg = ", ".join(ue.get("message", "Unknown error") for ue in user_errors)
                    return ToolResult(success=False, output="", error=error_msg)

                order = result.get("order")
                if not order:
                    return ToolResult(success=False, output="", error="Order update was not successful")

                return ToolResult(success=True, output=response.text, data=data)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")