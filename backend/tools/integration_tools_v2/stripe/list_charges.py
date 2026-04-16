from typing import Any, Dict
import httpx
import json
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class StripeListChargesTool(BaseTool):
    name = "Stripe List Charges"
    description = "List all charges"
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
                "limit": {
                    "type": "number",
                    "description": "Number of results to return (default 10, max 100)",
                },
                "customer": {
                    "type": "string",
                    "description": "Filter by customer ID",
                },
                "created": {
                    "type": "object",
                    "description": "Filter by creation date (e.g., {\"gt\": 1633024800})",
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
        
        url = "https://api.stripe.com/v1/charges"
        query_params: Dict[str, Any] = {}
        limit = parameters.get("limit")
        if limit is not None:
            query_params["limit"] = int(limit)
        customer = parameters.get("customer")
        if customer:
            query_params["customer"] = customer
        created = parameters.get("created")
        if created:
            for key, value in created.items():
                query_params[f"created[{key}]"] = str(value)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)
                
                if response.status_code == 200:
                    data = response.json()
                    transformed = {
                        "charges": data.get("data", []),
                        "metadata": {
                            "count": len(data.get("data", [])),
                            "has_more": data.get("has_more", False),
                        },
                    }
                    return ToolResult(success=True, output=json.dumps(transformed), data=transformed)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")