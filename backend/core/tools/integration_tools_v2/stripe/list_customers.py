from typing import Any, Dict
import httpx
import os
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class StripeListCustomersTool(BaseTool):
    name = "stripe_list_customers"
    description = "List all customers"
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
        if context:
            credentials = context.get("credentials", {})
            token = credentials.get("STRIPE_API_KEY")
        else:
            token = None
        if token is None:
            token = os.getenv("STRIPE_API_KEY")
        return token or ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "number",
                    "description": "Number of results to return (default 10, max 100)",
                },
                "email": {
                    "type": "string",
                    "description": "Filter by email address",
                },
                "created": {
                    "type": "object",
                    "description": "Filter by creation date",
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
        
        query_params: Dict[str, str] = {}
        limit = parameters.get("limit")
        if limit is not None:
            query_params["limit"] = str(limit)
        email = parameters.get("email")
        if email is not None:
            query_params["email"] = email
        created = parameters.get("created")
        if created:
            for key, value in created.items():
                query_params[f"created[{key}]"] = str(value)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")