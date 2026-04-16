from typing import Any, Dict
import httpx
import base64
import time
import json
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class KalshiCreateOrderTool(BaseTool):
    name = "kalshi_create_order"
    description = "Create a new order on a Kalshi prediction market"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="keyId",
                description="Your Kalshi API Key ID",
                env_var="KALSHI_KEY_ID",
                required=True,
                auth_type="api_key",
            ),
            CredentialRequirement(
                key="privateKey",
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
                    "description": "Market ticker identifier (e.g., \"KXBTC-24DEC31\", \"INX-25JAN03-T4485.99\")",
                },
                "side": {
                    "type": "string",
                    "description": "Side of the order: \"yes\" or \"no\"",
                },
                "action": {
                    "type": "string",
                    "description": "Action type: \"buy\" or \"sell\"",
                },
                "count": {
                    "type": "string",
                    "description": "Number of contracts to trade (e.g., \"10\", \"100\"). Provide count or countFp",
                },
                "type": {
                    "type": "string",
                    "description": "Order type: \"limit\" or \"market\" (default: \"limit\")",
                },
                "yesPrice": {
                    "type": "string",
                    "description": "Yes price in cents (1-99)",
                },
                "noPrice": {
                    "type": "string",
                    "description": "No price in cents (1-99)",
                },
                "yesPriceDollars": {
                    "type": "string",
                    "description": "Yes price in dollars (e.g., \"0.56\")",
                },
                "noPriceDollars": {
                    "type": "string",
                    "description": "No price in dollars (e.g., \"0.56\")",
                },
                "clientOrderId": {
                    "type": "string",
                    "description": "Custom order identifier",
                },
                "expirationTs": {
                    "type": "string",
                    "description": "Unix timestamp for order expiration",
                },
                "timeInForce": {
                    "type": "string",
                    "description": "Time in force: 'fill_or_kill', 'good_till_canceled', 'immediate_or_cancel'",
                },
                "buyMaxCost": {
                    "type": "string",
                    "description": "Maximum cost in cents (auto-enables fill_or_kill)",
                },
                "postOnly": {
                    "type": "string",
                    "description": "Set to 'true' for maker-only orders",
                },
                "reduceOnly": {
                    "type": "string",
                    "description": "Set to 'true' for position reduction only",
                },
                "selfTradePreventionType": {
                    "type": "string",
                    "description": "Self-trade prevention: 'taker_at_cross' or 'maker'",
                },
                "orderGroupId": {
                    "type": "string",
                    "description": "Associated order group ID",
                },
                "countFp": {
                    "type": "string",
                    "description": "Count in fixed-point for fractional contracts",
                },
                "cancelOrderOnPause": {
                    "type": "string",
                    "description": "Set to 'true' to cancel order on market pause",
                },
                "subaccount": {
                    "type": "string",
                    "description": "Subaccount to use for the order",
                },
            },
            "required": ["keyId", "privateKey", "ticker", "side", "action"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        key_id = parameters.get("keyId")
        private_key = parameters.get("privateKey")
        if self._is_placeholder_token(key_id) or self._is_placeholder_token(private_key):
            return ToolResult(success=False, output="", error="Kalshi API credentials not configured.")

        body: dict[str, Any] = {
            "ticker": parameters["ticker"],
            "side": parameters["side"].lower(),
            "action": parameters["action"].lower(),
        }
        if "count" in parameters:
            body["count"] = int(parameters["count"])
        if "countFp" in parameters:
            body["count_fp"] = parameters["countFp"]
        if "type" in parameters:
            body["type"] = parameters["type"].lower()
        if "yesPrice" in parameters:
            body["yes_price"] = int(parameters["yesPrice"])
        if "noPrice" in parameters:
            body["no_price"] = int(parameters["noPrice"])
        if "yesPriceDollars" in parameters:
            body["yes_price_dollars"] = parameters["yesPriceDollars"]
        if "noPriceDollars" in parameters:
            body["no_price_dollars"] = parameters["noPriceDollars"]
        if "clientOrderId" in parameters:
            body["client_order_id"] = parameters["clientOrderId"]
        if "expirationTs" in parameters:
            body["expiration_ts"] = int(parameters["expirationTs"])
        if "timeInForce" in parameters:
            body["time_in_force"] = parameters["timeInForce"]
        if "buyMaxCost" in parameters:
            body["buy_max_cost"] = int(parameters["buyMaxCost"])
        if "postOnly" in parameters:
            body["post_only"] = parameters["postOnly"] == "true"
        if "reduceOnly" in parameters:
            body["reduce_only"] = parameters["reduceOnly"] == "true"
        if "selfTradePreventionType" in parameters:
            body["self_trade_prevention_type"] = parameters["selfTradePreventionType"]
        if "orderGroupId" in parameters:
            body["order_group_id"] = parameters["orderGroupId"]
        if "cancelOrderOnPause" in parameters:
            body["cancel_order_on_pause"] = parameters["cancelOrderOnPause"] == "true"
        if "subaccount" in parameters:
            body["subaccount"] = parameters["subaccount"]

        body_str = json.dumps(body, separators=(",", ":"))
        timestamp = str(int(time.time()))
        method = "POST"
        path = "/trade-api/v2/portfolio/orders"
        message = f"{method}\n{path}\n{timestamp}\n{body_str}"

        try:
            private_key_obj = serialization.load_pem_private_key(
                private_key.encode("utf-8"), password=None
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Invalid private key: {str(e)}")

        try:
            signature = private_key_obj.sign(
                message.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256()
            )
            sig_b64 = base64.b64encode(signature).decode("utf-8")
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Signing failed: {str(e)}")

        headers = {
            "Key-Id": key_id,
            "Signature": sig_b64,
            "Content-Type": "application/json",
        }
        url = "https://trade-api.kalshi.com/trade-api/v2/portfolio/orders"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, content=body_str.encode("utf-8"))

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")