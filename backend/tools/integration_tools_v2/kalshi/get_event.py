from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class KalshiGetEventTool(BaseTool):
    name = "kalshi_get_event"
    description = "Retrieve details of a specific event by ticker (V2 - exact API response)"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="kalshi_access_token",
                description="Kalshi access token (API key used as Bearer token)",
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
                "eventTicker": {
                    "type": "string",
                    "description": "Event ticker identifier (e.g., \"KXBTC-24DEC31\", \"INX-25JAN03\")",
                },
                "withNestedMarkets": {
                    "type": "string",
                    "description": "Include nested markets in response (true/false)",
                },
            },
            "required": ["eventTicker"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = f"https://trading-api.kalshi.com/trade-api/v2/events/{parameters['eventTicker']}"
        query_params = []
        if parameters.get("withNestedMarkets"):
            query_params.append(f"with_nested_markets={parameters['withNestedMarkets']}")
        if query_params:
            url += "?" + "&".join(query_params)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")