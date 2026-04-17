from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class HubspotGetCartTool(BaseTool):
    name = "hubspot_get_cart"
    description = "Retrieve a single cart by ID from HubSpot"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="HUBSPOT_ACCESS_TOKEN",
                description="Access token for the HubSpot API",
                env_var="HUBSPOT_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "hubspot",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("HUBSPOT_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "cartId": {
                    "type": "string",
                    "description": "The HubSpot cart ID to retrieve",
                },
                "properties": {
                    "type": "string",
                    "description": "Comma-separated list of HubSpot property names to return",
                },
                "associations": {
                    "type": "string",
                    "description": "Comma-separated list of object types to retrieve associated IDs for",
                },
            },
            "required": ["cartId"],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        cart_id = parameters["cartId"].strip()
        url = f"https://api.hubapi.com/crm/v3/objects/carts/{cart_id}"
        params: Dict[str, str] = {}
        if prop := parameters.get("properties"):
            params["properties"] = prop
        if assoc := parameters.get("associations"):
            params["associations"] = assoc
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params)
                
                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    processed = {
                        "cart": data,
                        "cartId": data.get("id"),
                        "success": True,
                    }
                    return ToolResult(success=True, output=str(processed), data=processed)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")