from typing import Any, Dict
import httpx
import base64
import time
import urllib.parse
try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
except ImportError:
    hashes = serialization = padding = None
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class KalshiGetFillsTool(BaseTool):
    name = "kalshi_get_fills"
    description = "Retrieve your portfolio's fills/trades from Kalshi"
    category = "integration"

    @staticmethod
    def _is_placeholder_credential(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="kalshi_key_id",
                description="Your Kalshi API Key ID",
                env_var="KALSHI_KEY_ID",
                required=True,
                auth_type="api_key",
            ),
            CredentialRequirement(
                key="kalshi_private_key",
                description="Your RSA Private Key (PEM format)",
                env_var="KALSHI_PRIVATE_KEY",
                required=True,
                auth_type="api_key",
            ),
        ]

    def _build_auth_headers(self, key_id: str, private_key: str, method: str, path: str) -> Dict[str, str]:
        timestamp = str(int(time.time() * 1000))
        payload = f"{timestamp}:{method}:{path}"
        pkey = serialization.load_pem_private_key(
            private_key.encode("utf-8"),
            password=None,
        )
        signature = pkey.sign(
            payload.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        sig_b64 = base64.b64encode(signature).decode("utf-8")
        return {
            "keyId": key_id,
            "timestamp": timestamp,
            "signature": sig_b64,
        }

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": 'Filter by market ticker (e.g., "KXBTC-24DEC31")',
                },
                "orderId": {
                    "type": "string",
                    "description": 'Filter by order ID (e.g., "abc123-def456-ghi789")',
                },
                "minTs": {
                    "type": "number",
                    "description": 'Minimum timestamp in Unix milliseconds (e.g., 1704067200000)',
                },
                "maxTs": {
                    "type": "number",
                    "description": 'Maximum timestamp in Unix milliseconds (e.g., 1704153600000)',
                },
                "subaccount": {
                    "type": "string",
                    "description": 'Subaccount identifier to get fills for',
                },
                "limit": {
                    "type": "string",
                    "description": 'Number of results to return (1-200, default: 100)',
                },
                "cursor": {
                    "type": "string",
                    "description": 'Pagination cursor from previous response for fetching next page',
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        if serialization is None or hashes is None or padding is None:
            return ToolResult(success=False, output="", error="cryptography is not installed. Install it to use Kalshi trading tools.")

        key_id = context.get("kalshi_key_id") if context else None
        private_key = context.get("kalshi_private_key") if context else None

        if self._is_placeholder_credential(key_id) or self._is_placeholder_credential(private_key):
            return ToolResult(success=False, output="", error="Kalshi credentials not configured.")

        signing_path = "/trade-api/v2/portfolio/fills"
        headers = self._build_auth_headers(key_id, private_key, "GET", signing_path)

        query_params: Dict[str, str] = {}
        mapping = {
            "ticker": "ticker",
            "orderId": "order_id",
            "minTs": "min_ts",
            "maxTs": "max_ts",
            "subaccount": "subaccount",
            "limit": "limit",
            "cursor": "cursor",
        }
        for param_key, query_key in mapping.items():
            val = parameters.get(param_key)
            if val is not None:
                query_params[query_key] = str(val)

        url = f"https://trade-api.kalshi.com{signing_path}"
        query_string = urllib.parse.urlencode(query_params)
        if query_string:
            url += f"?{query_string}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
