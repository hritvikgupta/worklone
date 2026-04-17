from typing import Any, Dict
import httpx
import base64
import secrets
import time
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class KalshiGetBalanceTool(BaseTool):
    name = "kalshi_get_balance"
    description = "Retrieve your account balance and portfolio value from Kalshi (V2 - exact API response)"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return []

    def _build_kalshi_auth_headers(self, key_id: str, private_key: str, method: str, path: str) -> Dict[str, str]:
        nonce = secrets.token_urlsafe(32)
        timestamp = str(int(time.time()))
        message = nonce + timestamp + method.upper() + path
        pkey = serialization.load_pem_private_key(
            private_key.encode("utf-8"),
            password=None,
        )
        signature = pkey.sign(
            message.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        nonce_b64 = base64.b64encode(nonce.encode("utf-8")).decode("utf-8")
        timestamp_b64 = base64.b64encode(timestamp.encode("utf-8")).decode("utf-8")
        sig_b64 = base64.b64encode(signature).decode("utf-8")
        auth_header = f"kalshi-api-key-id/v1/{nonce_b64}:{timestamp_b64}:{sig_b64}"
        return {"Authorization": auth_header}

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
            },
            "required": ["keyId", "privateKey"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        key_id = parameters.get("keyId")
        private_key = parameters.get("privateKey")
        if not key_id or not private_key:
            return ToolResult(success=False, output="", error="Missing keyId or privateKey.")
        if self._is_placeholder_token(key_id) or self._is_placeholder_token(private_key):
            return ToolResult(success=False, output="", error="Access credentials contain placeholders.")

        path = "/trade-api/v2/portfolio/balance"
        url = f"https://trade-api.kalshi.com{path}"
        headers = self._build_kalshi_auth_headers(key_id, private_key, "GET", path)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    return ToolResult(success=True, output=response.text, data=data)
                else:
                    return ToolResult(
                        success=False, output="", error=f"API error {response.status_code}: {response.text}"
                    )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")