from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection

class ShopifyCreateCustomerTool(BaseTool):
    name = "Shopify Create Customer"
    description = "Create a new customer in your Shopify store"
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
                "email": {
                    "type": "string",
                    "description": "Customer email address",
                },
                "firstName": {
                    "type": "string",
                    "description": "Customer first name",
                },
                "lastName": {
                    "type": "string",
                    "description": "Customer last name",
                },
                "phone": {
                    "type": "string",
                    "description": "Customer phone number",
                },
                "note": {
                    "type": "string",
                    "description": "Note about the customer",
                },
                "tags": {
                    "type": "array",
                    "description": "Customer tags",
                },
                "addresses": {
                    "type": "array",
                    "description": "Customer addresses",
                },
            },
            "required": ["shopDomain"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        shop_domain = parameters["shopDomain"]
        email = (parameters.get("email") or "").strip()
        first_name = (parameters.get("firstName") or "").strip()
        last_name = (parameters.get("lastName") or "").strip()
        phone = (parameters.get("phone") or "").strip()

        if not any([bool(email), bool(first_name), bool(last_name), bool(phone)]):
            return ToolResult(
                success=False,
                output="",
                error="Customer must have at least one of: email, phone, firstName, or lastName",
            )

        input_data: Dict[str, Any] = {}
        if email:
            input_data["email"] = parameters["email"]
        if first_name:
            input_data["firstName"] = parameters["firstName"]
        if last_name:
            input_data["lastName"] = parameters["lastName"]
        if phone:
            input_data["phone"] = parameters["phone"]
        note = parameters.get("note")
        if note:
            input_data["note"] = note
        tags = parameters.get("tags")
        if isinstance(tags, list):
            input_data["tags"] = tags
        addresses = parameters.get("addresses")
        if isinstance(addresses, list):
            input_data["addresses"] = addresses

        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": access_token,
        }

        url = f"https://{shop_domain}/admin/api/2024-10/graphql.json"

        query = """
        mutation customerCreate($input: CustomerInput!) {
          customerCreate(input: $input) {
            customer {
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
                address1
                address2
                city
                province
                country
                zip
                phone
              }
              defaultAddress {
                address1
                city
                province
                country
                zip
              }
            }
            userErrors {
              field
              message
            }
          }
        }
        """

        json_body = {
            "query": query,
            "variables": {"input": input_data},
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=json_body)

                if response.status_code not in [200, 201, 204]:
                    return ToolResult(success=False, output="", error=response.text)

                data = response.json()

                if "errors" in data and data["errors"]:
                    error_msg = data["errors"][0].get("message", "Failed to create customer")
                    return ToolResult(success=False, output="", error=error_msg)

                result = data.get("data", {}).get("customerCreate", {})
                user_errors = result.get("userErrors", [])
                if user_errors:
                    error_msgs = ", ".join([ue.get("message", "") for ue in user_errors])
                    return ToolResult(success=False, output="", error=error_msgs)

                customer = result.get("customer")
                if not customer:
                    return ToolResult(success=False, output="", error="Customer creation was not successful")

                return ToolResult(success=True, output=response.text, data={"customer": customer})

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")