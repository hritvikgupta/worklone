from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class KalshiGetCandlesticksTool(BaseTool):
    name = "kalshi_get_candlesticks"
    description = "Retrieve OHLC candlestick data for a specific market (V2 - full API response)"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="kalshi_api_key",
                description="Kalshi API key",
                env_var="KALSHI_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "kalshi",
            context=context,
            context_token_keys=("kalshi_api_key",),
            env_token_keys=("KALSHI_API_KEY",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "seriesTicker": {
                    "type": "string",
                    "description": 'Series ticker identifier (e.g., "KXBTC", "INX", "FED-RATE")',
                },
                "ticker": {
                    "type": "string",
                    "description": 'Market ticker identifier (e.g., "KXBTC-24DEC31", "INX-25JAN03-T4485.99")',
                },
                "startTs": {
                    "type": "number",
                    "description": 'Start timestamp in Unix seconds (e.g., 1704067200)',
                },
                "endTs": {
                    "type": "number",
                    "description": 'End timestamp in Unix seconds (e.g., 1704153600)',
                },
                "periodInterval": {
                    "type": "number",
                    "description": 'Period interval: 1 (1 minute), 60 (1 hour), or 1440 (1 day)',
                },
            },
            "required": ["seriesTicker", "ticker", "startTs", "endTs", "periodInterval"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        series_ticker = parameters["seriesTicker"]
        ticker = parameters["ticker"]
        start_ts = parameters["startTs"]
        end_ts = parameters["endTs"]
        period_interval = parameters["periodInterval"]
        
        url = f"https://trading-api.kalshi.com/trade-api/v2/series/{series_ticker}/markets/{ticker}/candlesticks?start_ts={start_ts}&end_ts={end_ts}&period_interval={period_interval}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")