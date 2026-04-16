from typing import Any, Dict
import httpx
import base64
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class KalshiGetOrderbookTool(BaseTool):
    name = "kalshi_get_orderbook"
    description = "Retrieve the orderbook (yes and no bids) for a specific market (V2 - includes depth and fp fields)"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="KALSHI_ACCESS_TOKEN",
                description="Kalshi access token",
                env_var="KALSHI_ACCESS_TOKEN",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "kalshi",
            context=context,
            context_token_keys=("kalshi_token",),
            env_token_keys=("KALSHI_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": 'Market ticker identifier (e.g., "KXBTC-24DEC31", "INX-25JAN03-T4485.99")',
                },
                "depth": {
                    "type": "number",
                    "description": "Number of price levels to return (e.g., 10, 20). Default: all levels",
                },
            },
            "required": ["ticker"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        ticker = parameters["ticker"]
        url = f"https://trading-api.kalshi.com/trade-api/v2/markets/{ticker}/orderbook"
        depth = parameters.get("depth")
        if depth is not None:
            url += f"?depth={depth}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")