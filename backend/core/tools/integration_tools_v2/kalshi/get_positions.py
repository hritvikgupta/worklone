from typing import Any, Dict
import httpx
import time
import jwt
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class KalshiGetPositionsTool(BaseTool):
    name = "kalshi_get_positions"
    description = "Retrieve your open positions from Kalshi"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="keyId",
                description="Kalshi API Key ID",
                env_var="KALSHI_KEY_ID",
                required=True,
                auth_type="api_key",
            ),
            CredentialRequirement(
                key="privateKey",
                description="Kalshi RSA Private Key (PEM format)",
                env_var="KALSHI_PRIVATE_KEY",
                required=True,
                auth_type="api_key",
            ),
        ]

    def _build_kalshi_auth_headers(self, key_id: str, private_key: str, method: str, path: str) -> Dict[str, str]:
        now = int(time.time())
        payload = {
            "iat": now,
            "exp": now + 120,
            "method": method.upper(),
            "path": path,
        }
        jwt_headers = {"kid": key_id}
        token = jwt.encode(payload, private_key, algorithm="RS256", headers=jwt_headers)
        return {
            "kid": key_id,
            "Authorization": token,
        }

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "keyId": {
                    "type": "string",
                    "description": "Your Kalshi API Key ID",
                },
                "privateKey": {
                    "type": "string",
                    "description": "Your RSA Private Key (PEM format)",
                },
                "ticker": {
                    "type": "string",
                    "description": "Filter by market ticker (e.g., \"KXBTC-24DEC31\")",
                },
                "eventTicker": {
                    "type": "string",
                    "description": "Filter by event ticker, max 10 comma-separated (e.g., \"KXBTC-24DEC31,INX-25JAN03\")",
                },
                "countFilter": {
                    "type": "string",
                    "description": "Filter by count: \"all\", \"positive\", or \"negative\" (default: \"all\")",
                },
                "subaccount": {
                    "type": "string",
                    "description": "Subaccount identifier to get positions for",
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
            "required": ["keyId", "privateKey"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        key_id = parameters.get("keyId", "")
        private_key = parameters.get("privateKey", "")
        if self._is_placeholder_token(key_id) or self._is_placeholder_token(private_key):
            return ToolResult(success=False, output="", error="Kalshi credentials not configured.")
        url = "https://trade-api.kalshi.com/trade-api/v2/portfolio/positions"
        query_params: Dict[str, str] = {}
        param_mappings = [
            ("ticker", "ticker"),
            ("event_ticker", "eventTicker"),
            ("count_filter", "countFilter"),
            ("subaccount", "subaccount"),
            ("limit", "limit"),
            ("cursor", "cursor"),
        ]
        for query_key, param_key in param_mappings:
            value = parameters.get(param_key)
            if value:
                query_params[query_key] = str(value)
        path_for_auth = "/trade-api/v2/portfolio/positions"
        headers = self._build_kalshi_auth_headers(key_id, private_key, "GET", path_for_auth)
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")