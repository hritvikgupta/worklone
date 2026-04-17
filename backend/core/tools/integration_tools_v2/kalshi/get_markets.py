from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class KalshiGetMarketsTool(BaseTool):
    name = "kalshi_get_markets_v2"
    description = "Retrieve a list of prediction markets from Kalshi with all filtering options (V2 - full API response)"
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
                auth_type="oauth",
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

    def _build_query_params(self, parameters: dict) -> Dict[str, str]:
        mapping = {
            "status": "status",
            "series_ticker": "seriesTicker",
            "event_ticker": "eventTicker",
            "min_created_ts": "minCreatedTs",
            "max_created_ts": "maxCreatedTs",
            "min_updated_ts": "minUpdatedTs",
            "min_close_ts": "minCloseTs",
            "max_close_ts": "maxCloseTs",
            "min_settled_ts": "minSettledTs",
            "max_settled_ts": "maxSettledTs",
            "tickers": "tickers",
            "mve_filter": "mveFilter",
            "limit": "limit",
            "cursor": "cursor",
        }
        query_params: Dict[str, str] = {}
        for query_key, param_key in mapping.items():
            value = parameters.get(param_key)
            if value:
                query_params[query_key] = str(value)
        return query_params

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": 'Filter by market status: "unopened", "open", "closed", or "settled"',
                },
                "seriesTicker": {
                    "type": "string",
                    "description": 'Filter by series ticker (e.g., "KXBTC", "INX", "FED-RATE")',
                },
                "eventTicker": {
                    "type": "string",
                    "description": 'Filter by event ticker (e.g., "KXBTC-24DEC31", "INX-25JAN03")',
                },
                "minCreatedTs": {
                    "type": "number",
                    "description": "Minimum created timestamp in Unix seconds (e.g., 1704067200)",
                },
                "maxCreatedTs": {
                    "type": "number",
                    "description": "Maximum created timestamp in Unix seconds (e.g., 1704153600)",
                },
                "minUpdatedTs": {
                    "type": "number",
                    "description": "Minimum updated timestamp in Unix seconds (e.g., 1704067200)",
                },
                "minCloseTs": {
                    "type": "number",
                    "description": "Minimum close timestamp in Unix seconds (e.g., 1704067200)",
                },
                "maxCloseTs": {
                    "type": "number",
                    "description": "Maximum close timestamp in Unix seconds (e.g., 1704153600)",
                },
                "minSettledTs": {
                    "type": "number",
                    "description": "Minimum settled timestamp in Unix seconds (e.g., 1704067200)",
                },
                "maxSettledTs": {
                    "type": "number",
                    "description": "Maximum settled timestamp in Unix seconds (e.g., 1704153600)",
                },
                "tickers": {
                    "type": "string",
                    "description": 'Comma-separated list of tickers (e.g., "KXBTC-24DEC31,INX-25JAN03")',
                },
                "mveFilter": {
                    "type": "string",
                    "description": 'MVE filter: "display" or "all"',
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
        
        url = "https://trading-api.kalshi.com/trade-api/v2/markets"
        query_params = self._build_query_params(parameters)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)
                
                if response.status_code == 200:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")