from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class StripeCreateCustomerTool(BaseTool):
    name = "stripe_create_customer"
    description = "Create a new customer object"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="STRIPE_API_KEY",
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
            context_token_keys=("apiKey",),
            env_token_keys=("STRIPE_API_KEY",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "email": {
                    "type": "string",
                    "description": "Customer email address",
                },
                "name": {
                    "type": "string",
                    "description": "Customer full name",
                },
                "phone": {
                    "type": "string",
                    "description": "Customer phone number",
                },
                "description": {
                    "type": "string",
                    "description": "Description of the customer",
                },
                "address": {
                    "type": "object",
                    "description": "Customer address object",
                },
                "metadata": {
                    "type": "object",
                    "description": "Set of key-value pairs",
                },
                "payment_method": {
                    "type": "string",
                    "description": "Payment method ID to attach",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        url = "https://api.stripe.com/v1/customers"

        form_data: Dict[str, str] = {}
        for field in ["email", "name", "phone", "description", "payment_method"]:
            if parameters.get(field):
                form_data[field] = parameters[field]

        if parameters.get("address"):
            for key, value in parameters["address"].items():
                if value is not None:
                    form_data[f"address[{key}]"] = str(value)

        if parameters.get("metadata"):
            for key, value in parameters["metadata"].items():
                if value is not None:
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