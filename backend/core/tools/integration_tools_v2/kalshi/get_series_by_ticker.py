from typing import Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection

class KalshiGetSeriesByTickerTool(BaseTool):
    name = "kalshi_get_series_by_ticker"
    description = "Retrieve details of a specific market series by ticker"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="kalshi_access_token",
                description="Kalshi API token (Bearer token from Kalshi dashboard)",
                env_var="KALSHI_ACCESS_TOKEN",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "kalshi",
            context=context,
            context_token_keys=("kalshi_access_token",),
            env_token_keys=("KALSHI_ACCESS_TOKEN",),
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
                "includeVolume": {
                    "type": "string",
                    "description": "Include volume data in response (true/false)",
                },
            },
            "required": ["seriesTicker"],
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
        url = f"https://trading-api.kalshi.com/trade-api/v2/series/{series_ticker}"
        include_volume = parameters.get("includeVolume")
        if include_volume:
            url += f"?include_volume={include_volume}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")