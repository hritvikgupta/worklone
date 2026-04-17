from typing import Any, Dict
import httpx
import urllib.parse
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class KalshiGetEventsTool(BaseTool):
    name = "kalshi_get_events"
    description = "Retrieve a list of events from Kalshi with optional filtering (V2 - exact API response)"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="KALSHI_ACCESS_TOKEN",
                description="Access token",
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

    def _build_url(self, parameters: dict) -> str:
        base_url = "https://trading-api.kalshi.com/trade-api/v2/events"
        query_params = []
        status = parameters.get("status")
        if status:
            query_params.append(("status", status))
        series_ticker = parameters.get("seriesTicker")
        if series_ticker:
            query_params.append(("series_ticker", series_ticker))
        with_nested_markets = parameters.get("withNestedMarkets")
        if with_nested_markets:
            query_params.append(("with_nested_markets", with_nested_markets))
        with_milestones = parameters.get("withMilestones")
        if with_milestones:
            query_params.append(("with_milestones", with_milestones))
        min_close_ts = parameters.get("minCloseTs")
        if min_close_ts is not None:
            query_params.append(("min_close_ts", str(min_close_ts)))
        limit = parameters.get("limit")
        if limit:
            query_params.append(("limit", limit))
        cursor = parameters.get("cursor")
        if cursor:
            query_params.append(("cursor", cursor))
        if query_params:
            query_string = urllib.parse.urlencode(query_params)
            return f"{base_url}?{query_string}"
        return base_url

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": 'Filter by event status: "open", "closed", or "settled"',
                },
                "seriesTicker": {
                    "type": "string",
                    "description": 'Filter by series ticker (e.g., "KXBTC", "INX", "FED-RATE")',
                },
                "withNestedMarkets": {
                    "type": "string",
                    "description": 'Include nested markets in response: "true" or "false"',
                },
                "withMilestones": {
                    "type": "string",
                    "description": 'Include milestones in response: "true" or "false"',
                },
                "minCloseTs": {
                    "type": "number",
                    "description": "Minimum close timestamp in Unix seconds (e.g., 1704067200)",
                },
                "limit": {
                    "type": "string",
                    "description": "Number of results to return (1-200, default: 200)",
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
        
        url = self._build_url(parameters)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("error", {}).get("message", response.text) if isinstance(error_data, dict) else response.text
                    except:
                        error_msg = response.text
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")