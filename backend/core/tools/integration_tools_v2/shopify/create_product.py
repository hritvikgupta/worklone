from typing import Any, Dict, List
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ShopifyCreateProductTool(BaseTool):
    name = "shopify_create_product"
    description = "Create a new product in your Shopify store"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="SHOPIFY_ACCESS_TOKEN",
                description="Access token for Shopify",
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
                "title": {
                    "type": "string",
                    "description": "Product title",
                },
                "descriptionHtml": {
                    "type": "string",
                    "description": "Product description (HTML)",
                },
                "vendor": {
                    "type": "string",
                    "description": "Product vendor/brand",
                },
                "productType": {
                    "type": "string",
                    "description": "Product type/category",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Product tags",
                },
                "status": {
                    "type": "string",
                    "description": "Product status (ACTIVE, DRAFT, ARCHIVED)",
                },
            },
            "required": ["shopDomain", "title"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        shop_domain = parameters.get("shopDomain")
        if not shop_domain:
            return ToolResult(success=False, output="", error="shopDomain is required.")

        title = parameters.get("title", "").strip()
        if not title:
            return ToolResult(success=False, output="", error="Title is required to create a Shopify product.")

        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": access_token,
        }

        url = f"https://{shop_domain}/admin/api/2024-10/graphql.json"

        input_data: Dict[str, Any] = {
            "title": title,
        }
        for field in ["descriptionHtml", "vendor", "productType", "status"]:
            value = parameters.get(field)
            if value:
                input_data[field] = value
        tags = parameters.get("tags")
        if tags:
            input_data["tags"] = tags

        body = {
            "query": """
                mutation productCreate($input: ProductInput!) {
                  productCreate(input: $input) {
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
                "input": input_data,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code not in [200, 201, 204]:
                    return ToolResult(success=False, output="", error=response.text)

                try:
                    data = response.json()
                except Exception:
                    return ToolResult(success=False, output="", error="Invalid JSON response from Shopify API.")

                if "errors" in data and data["errors"]:
                    error = data["errors"][0].get("message", "Failed to create product")
                    return ToolResult(success=False, output="", error=error)

                result = data.get("data", {}).get("productCreate", {})
                user_errors = result.get("userErrors", [])
                if user_errors:
                    error_msgs = [ue.get("message", "Unknown error") for ue in user_errors]
                    return ToolResult(success=False, output="", error=", ".join(error_msgs))

                product = result.get("product")
                if not product:
                    return ToolResult(success=False, output="", error="Product creation was not successful")

                output_data = {
                    "product": {
                        "id": product.get("id"),
                        "title": product.get("title"),
                        "handle": product.get("handle"),
                        "descriptionHtml": product.get("descriptionHtml"),
                        "vendor": product.get("vendor"),
                        "productType": product.get("productType"),
                        "tags": product.get("tags"),
                        "status": product.get("status"),
                        "createdAt": product.get("createdAt"),
                        "updatedAt": product.get("updatedAt"),
                        "variants": product.get("variants", []),
                        "images": product.get("images", []),
                    }
                }

                return ToolResult(
                    success=True,
                    output=json.dumps(output_data),
                    data=output_data,
                )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")