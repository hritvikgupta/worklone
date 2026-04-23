from typing import Dict, Any
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ShopifyUpdateProductTool(BaseTool):
    name = "shopify_update_product"
    description = "Update an existing product in your Shopify store"
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
                "productId": {
                    "type": "string",
                    "description": "Product ID to update (gid://shopify/Product/123456789)",
                },
                "title": {
                    "type": "string",
                    "description": "New product title",
                },
                "descriptionHtml": {
                    "type": "string",
                    "description": "New product description (HTML)",
                },
                "vendor": {
                    "type": "string",
                    "description": "New product vendor/brand",
                },
                "productType": {
                    "type": "string",
                    "description": "New product type/category",
                },
                "tags": {
                    "type": "array",
                    "items": {
                        "type": "string",
                    },
                    "description": "New product tags",
                },
                "status": {
                    "type": "string",
                    "description": "New product status (ACTIVE, DRAFT, ARCHIVED)",
                },
            },
            "required": ["shopDomain", "productId"],
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

        input_ = {
            "id": parameters["productId"],
        }
        fields = ["title", "descriptionHtml", "vendor", "productType", "tags", "status"]
        for field in fields:
            if field in parameters:
                input_[field] = parameters[field]

        body = {
            "query": """
                mutation productUpdate($input: ProductInput!) {
                  productUpdate(input: $input) {
                    product {
                      id
                      title
                      handle
                      descriptionHtml
                      vendor
                      productType
                      tags
                      status
                      createdAt
                      updatedAt
                      variants(first: 10) {
                        edges {
                          node {
                            id
                            title
                            price
                            compareAtPrice
                            sku
                            inventoryQuantity
                          }
                        }
                      }
                      images(first: 10) {
                        edges {
                          node {
                            id
                            url
                            altText
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
            """,
            "variables": {
                "input": input_,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code != 200:
                    return ToolResult(success=False, output="", error=response.text)

                data = response.json()

                if "errors" in data and data["errors"]:
                    error_msg = data["errors"][0].get("message", "Failed to update product")
                    return ToolResult(success=False, output="", error=error_msg)

                result = data.get("data", {}).get("productUpdate")
                if not result:
                    return ToolResult(success=False, output="", error="Product update was not successful")

                user_errors = result.get("userErrors", [])
                if user_errors:
                    error_msg = ", ".join(ue.get("message", "") for ue in user_errors)
                    return ToolResult(success=False, output="", error=error_msg)

                product = result.get("product")
                if not product:
                    return ToolResult(success=False, output="", error="Product update was not successful")

                return ToolResult(success=True, output=response.text, data={"product": product})

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")