from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class StripeUpdateProductTool(BaseTool):
    name = "stripe_update_product"
    description = "Update an existing product"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="stripe_api_key",
                description="Stripe API key (secret key)",
                env_var="STRIPE_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "stripe",
            context=context,
            context_token_keys=("stripe_api_key", "api_key"),
            env_token_keys=("STRIPE_API_KEY",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "description": "Product ID (e.g., prod_1234567890)",
                },
                "name": {
                    "type": "string",
                    "description": "Updated product name",
                },
                "description": {
                    "type": "string",
                    "description": "Updated product description",
                },
                "active": {
                    "type": "boolean",
                    "description": "Updated active status",
                },
                "images": {
                    "type": "array",
                    "items": {
                        "type": "string",
                    },
                    "description": "Updated array of image URLs",
                },
                "metadata": {
                    "type": "object",
                    "additionalProperties": True,
                    "description": "Updated metadata",
                },
            },
            "required": ["id"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        
        url = f"https://api.stripe.com/v1/products/{parameters['id']}"
        
        form_data: dict[str, str] = {}
        name = parameters.get("name")
        if name:
            form_data["name"] = name
        description = parameters.get("description")
        if description:
            form_data["description"] = description
        active = parameters.get("active")
        if active is not None:
            form_data["active"] = "true" if active else "false"
        images = parameters.get("images", [])
        for index, image in enumerate(images):
            form_data[f"images[{index}]"] = image
        metadata = parameters.get("metadata", {})
        for key, value in metadata.items():
            form_data[f"metadata[{key}]"] = str(value)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, data=form_data)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")