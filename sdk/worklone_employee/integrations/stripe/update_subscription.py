from typing import Any, Dict
import httpx
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement

class StripeUpdateSubscriptionTool(BaseTool):
    name = "stripe_update_subscription"
    description = "Update an existing subscription"
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

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "description": "Subscription ID (e.g., sub_1234567890)",
                },
                "items": {
                    "type": "array",
                    "description": "Updated array of items with price IDs",
                    "items": {
                        "type": "object",
                        "properties": {
                            "price": {
                                "type": "string",
                            },
                            "quantity": {
                                "type": "integer",
                            },
                        },
                        "required": ["price"],
                    },
                },
                "cancel_at_period_end": {
                    "type": "boolean",
                    "description": "Cancel subscription at period end",
                },
                "metadata": {
                    "type": "object",
                    "description": "Updated metadata",
                    "additionalProperties": True,
                },
            },
            "required": ["id"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        stripe_api_key = context.get("stripe_api_key") if context else None
        if self._is_placeholder_token(stripe_api_key or ""):
            return ToolResult(success=False, output="", error="Stripe API key not configured.")

        id_ = parameters["id"]
        url = f"https://api.stripe.com/v1/subscriptions/{id_}"

        form_data: Dict[str, str] = {}
        items = parameters.get("items")
        if items and isinstance(items, list):
            for index, item in enumerate(items):
                if isinstance(item, dict) and "price" in item:
                    form_data[f"items[{index}][price]"] = str(item["price"])
                    quantity = item.get("quantity")
                    if quantity is not None:
                        form_data[f"items[{index}][quantity]"] = str(quantity)

        cancel_at_period_end = parameters.get("cancel_at_period_end")
        if cancel_at_period_end is not None:
            form_data["cancel_at_period_end"] = str(cancel_at_period_end).lower()

        metadata = parameters.get("metadata")
        if metadata and isinstance(metadata, dict):
            for key, value in metadata.items():
                form_data[f"metadata[{key}]"] = str(value)

        headers = {
            "Authorization": f"Bearer {stripe_api_key}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, data=form_data)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")