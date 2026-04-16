from typing import Any, Dict
import httpx
import base64
import json
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class KalshiAmendOrderTool(BaseTool):
    name = "kalshi_amend_order"
    description = "Modify the price or quantity of an existing order on Kalshi (V2 with full API response)"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="KALSHI_KEY_ID",
                description="Your Kalshi API Key ID",
                env_var="KALSHI_KEY_ID",
                required=True,
                auth_type="api_key",
            ),
            CredentialRequirement(
                key="KALSHI_PRIVATE_KEY",
                description="Your RSA Private Key (PEM format)",
                env_var="KALSHI_PRIVATE_KEY",
                required=True,
                auth_type="api_key",
            ),
        ]

    def _sign_message(self, private_key_pem: str, message: str) -> str:
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode("utf-8"),
            password=None,
        )
        signature = private_key.sign(
            message.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return base64.b64encode(signature).decode("utf-8")

    def _build_body(self, parameters: dict[str, str]) -> dict[str, Any]:
        body: dict[str, Any] = {
            "ticker": parameters["ticker"],
            "side": parameters["side"].lower(),
            "action": parameters["action"].lower(),
        }
        optional_mappings = [
            ("clientOrderId", "client_order_id"),
            ("updatedClientOrderId", "updated_client_order_id"),
            ("count", "count", int),
            ("yesPrice", "yes_price", int),
            ("noPrice", "no_price", int),
            ("yesPriceDollars", "yes_price_dollars"),
            ("noPriceDollars", "no_price_dollars"),
            ("countFp", "count_fp"),
        ]
        for param_key, body_key, *converter in optional_mappings:
            if param_key in parameters and parameters[param_key]:
                value = parameters[param_key]
                if converter:
                    value = converter[0](value)
                body[body_key] = value
        return body

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "orderId": {
                    "type": "string",
                    "description": 'Order ID to amend (e.g., "abc123-def456-ghi789")',
                },
                "ticker": {
                    "type": "string",
                    "description": 'Market ticker identifier (e.g., "KXBTC-24DEC31", "INX-25JAN03-T4485.99")',
                },
                "side": {
                    "type": "string",
                    "description": 'Side of the order: "yes" or "no"',
                },
                "action": {
                    "type": "string",
                    "description": 'Action type: "buy" or "sell"',
                },
                "clientOrderId": {
                    "type": "string",
                    "description": "Original client-specified order ID",
                },
                "updatedClientOrderId": {
                    "type": "string",
                    "description": "New client-specified order ID after amendment",
                },
                "count": {
                    "type": "string",
                    "description": 'Updated quantity for the order (e.g., "10", "100")',
                },
                "yesPrice": {
                    "type": "string",
                    "description": "Updated yes price in cents (1-99)",
                },
                "noPrice": {
                    "type": "string",
                    "description": "Updated no price in cents (1-99)",
                },
                "yesPriceDollars": {
                    "type": "string",
                    "description": 'Updated yes price in dollars (e.g., "0.56")',
                },
                "noPriceDollars": {
                    "type": "string",
                    "description": 'Updated no price in dollars (e.g., "0.56")',
                },
                "countFp": {
                    "type": "string",
                    "description": "Count in fixed-point for fractional contracts",
                },
            },
            "required": ["orderId", "ticker", "side", "action"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        key_id = context.get("KALSHI_KEY_ID", "") if context else ""
        private_key = context.get("KALSHI_PRIVATE_KEY", "") if context else ""

        if self._is_placeholder_token(key_id) or self._is_placeholder_token(private_key):
            return ToolResult(success=False, output="", error="Kalshi API credentials not configured.")

        order_id = parameters["orderId"]
        url = f"https://trade-api.kalshi.com/trade-api/v2/portfolio/orders/{order_id}/amend"
        path_for_sign = f"/trade-api/v2/portfolio/orders/{order_id}/amend"

        body = self._build_body(parameters)
        json_str = json.dumps(body, separators=(",", ":"))
        message = f"POST\n{path_for_sign}\n{json_str}"

        try:
            signature = self._sign_message(private_key, message)
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Signature error: {str(e)}")

        headers = {
            "Key-Id": key_id,
            "Signature": signature,
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, content=json_str.encode("utf-8"))

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")