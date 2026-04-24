from typing import Any, Dict
import httpx
import base64
import time
import secrets
try:
    from cryptography.hazmat.primitives import serialization, hashes
    from cryptography.hazmat.primitives.asymmetric import padding
except ImportError:
    serialization = hashes = padding = None
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class KalshiCancelOrderTool(BaseTool):
    name = "kalshi_cancel_order"
    description = "Cancel an existing order on Kalshi"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
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

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "orderId": {
                    "type": "string",
                    "description": "Order ID to cancel (e.g., \"abc123-def456-ghi789\")",
                },
            },
            "required": ["orderId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        if serialization is None or hashes is None or padding is None:
            return ToolResult(success=False, output="", error="cryptography is not installed. Install it to use Kalshi trading tools.")

        order_id = parameters.get("orderId")
        if not order_id:
            return ToolResult(success=False, output="", error="orderId is required.")

        key_id = context.get("kalshi_key_id") if context else None
        private_key = context.get("kalshi_private_key") if context else None

        if self._is_placeholder_token(key_id or "") or self._is_placeholder_token(private_key or ""):
            return ToolResult(success=False, output="", error="Kalshi credentials not configured.")

        url = f"https://trade-api.kalshi.com/trade-api/v2/portfolio/orders/{order_id}"
        path = f"/trade-api/v2/portfolio/orders/{order_id}"
        method = "DELETE"

        timestamp = str(int(time.time() * 1000))
        nonce = secrets.token_urlsafe(16)
        payload = f"{method}\n{path}\n{timestamp}\n{nonce}".encode("utf-8")

        try:
            private_key_obj = serialization.load_pem_private_key(
                private_key.encode("utf-8"),
                password=None,
            )
            signature = private_key_obj.sign(
                payload,
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
            signature_b64 = base64.b64encode(signature).decode("utf-8")
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Invalid private key: {str(e)}")

        headers = {
            "key-id": key_id,
            "timestamp": timestamp,
            "nonce": nonce,
            "signature": signature_b64,
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)

                if response.status_code in [200, 201, 204]:
                    try:
                        data = response.json()
                    except Exception:
                        data = {}
                    return ToolResult(success=True, output=response.text, data=data)
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
