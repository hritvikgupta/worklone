from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ShopifyGetCustomerTool(BaseTool):
    name = "shopify_get_customer"
    description = "Get a single customer by ID from your Shopify store"
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
                "customerId": {
                    "type": "string",
                    "description": "Customer ID (gid://shopify/Customer/123456789)",
                },
            },
            "required": ["shopDomain", "customerId"],
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
        customer_id = parameters["customerId"]
        url = f"https://{shop_domain}/admin/api/2024-10/graphql.json"
        
        body = {
            "query": """
            query getCustomer($id: ID!) {
              customer(id: $id) {
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
                addresses {
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
                defaultAddress {
                  firstName
                  lastName
                  address1
                  address2
                  city
                  province
                  country
                  zip
                }
              }
            }
            """,
            "variables": {
                "id": customer_id,
            },
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code != 200:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                
                if "errors" in data:
                    error_msg = data["errors"][0].get("message", "Failed to get customer") if data["errors"] else "Unknown GraphQL error"
                    return ToolResult(success=False, output="", error=error_msg)
                
                customer = data.get("data", {}).get("customer")
                if not customer:
                    return ToolResult(success=False, output="", error="Customer not found")
                
                return ToolResult(success=True, output=response.text, data={"customer": customer})
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")