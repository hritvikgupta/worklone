from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class KalshiGetTradesTool(BaseTool):
    name = "kalshi_get_trades"
    description = "Retrieve recent trades with additional filtering options (includes trade_id and count_fp)"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="KALSHI_ACCESS_TOKEN",
                description="Kalshi API access token",
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
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Filter by market ticker (e.g., \"KXBTC-24DEC31\")",
                },
                "minTs": {
                    "type": "number",
                    "description": "Minimum timestamp in Unix seconds (e.g., 1704067200)",
                },
                "maxTs": {
                    "type": "number",
                    "description": "Maximum timestamp in Unix seconds (e.g., 1704153600)",
                },
                "limit": {
                    "type": "string",
                    "description": "Number of results to return (1-1000, default: 100)",
                },
                "cursor": {
                    "type": "string",
                    "description": "Pagination cursor from previous response for fetching next page",
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
            "Content-Type": "application/json",
        }
        
        url = "https://trading-api.kalshi.com/trade-api/v2/markets/trades"
        
        query_params: Dict[str, str] = {}
        if "ticker" in parameters:
            query_params["ticker"] = parameters["ticker"]
        if "minTs" in parameters and parameters["minTs"] is not None:
            query_params["min_ts"] = str(parameters["minTs"])
        if "maxTs" in parameters and parameters["maxTs"] is not None:
            query_params["max_ts"] = str(parameters["maxTs"])
        if "limit" in parameters:
            query_params["limit"] = parameters["limit"]
        if "cursor" in parameters:
            query_params["cursor"] = parameters["cursor"]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")