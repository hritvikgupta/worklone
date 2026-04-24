from typing import Any, Dict
import httpx
import base64
import os
import time
import secrets
from hashlib import sha256
try:
    from cryptography.hazmat.primitives import serialization, hashes
    from cryptography.hazmat.primitives.asymmetric import padding
except ImportError:
    serialization = hashes = padding = None
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class KalshiGetOrderTool(BaseTool):
    name = "kalshi_get_order"
    description = "Retrieve details of a specific order by ID from Kalshi (V2 with full API response)"
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

    def _resolve_credentials(self, context: dict | None) -> tuple[str | None, str | None]:
        key_id = context.get("kalshi_key_id") if context else os.getenv("KALSHI_KEY_ID", "")
        private_key = context.get("kalshi_private_key") if context else os.getenv("KALSHI_PRIVATE_KEY", "")
        return key_id, private_key

    def _build_kalshi_auth_headers(self, key_id: str, private_key_pem: str, method: str, path: str) -> Dict[str, str]:
        nonce = secrets.token_urlsafe(32)
        timestamp = str(int(time.time() * 1000))
        body_hash = sha256(b"").hexdigest()
        message = f"{nonce}\n{timestamp}\n{method}\n{path}\n{body_hash}".encode("utf-8")
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode("utf-8"),
            password=None,
        )
        signature = private_key.sign(
            message,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        signature_b64 = base64.b64encode(signature).decode("utf-8")
        return {
            "kalshi-key-id": key_id,
            "kalshi-nonce": nonce,
            "kalshi-timestamp": timestamp,
            "kalshi-signature": signature_b64,
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
                "orderId": {
                    "type": "string",
                    "description": "Order ID to retrieve (e.g., \"abc123-def456-ghi789\")",
                },
            },
            "required": ["keyId", "privateKey", "orderId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        if serialization is None or hashes is None or padding is None:
            return ToolResult(success=False, output="", error="cryptography is not installed. Install it to use Kalshi trading tools.")

        key_id, private_key = self._resolve_credentials(context)
        
        if self._is_placeholder_token(key_id) or self._is_placeholder_token(private_key):
            return ToolResult(success=False, output="", error="Kalshi API credentials not configured.")
        
        order_id = parameters["orderId"]
        path = f"/trade-api/v2/portfolio/orders/{order_id}"
        url = f"https://trade-api.kalshi.com/trade-api/v2/portfolio/orders/{order_id}"
        
        headers = self._build_kalshi_auth_headers(key_id, private_key, "GET", path)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
