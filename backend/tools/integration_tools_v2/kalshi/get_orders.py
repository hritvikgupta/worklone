from typing import Any, Dict, Tuple
import httpx
import base64
import os
import time
from urllib.parse import urlencode
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class KalshiGetOrdersTool(BaseTool):
    name = "kalshi_get_orders"
    description = "Retrieve your orders from Kalshi with optional filtering (V2 with full API response)"
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

    def _get_credentials(self, context: dict | None) -> Tuple[str | None, str | None]:
        key_id = context.get("kalshi_key_id") if context else None
        if key_id is None:
            key_id = os.environ.get("KALSHI_KEY_ID")
        private_key_pem = context.get("kalshi_private_key") if context else None
        if private_key_pem is None:
            private_key_pem = os.environ.get("KALSHI_PRIVATE_KEY")
        return key_id, private_key_pem

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

    def _get_auth_headers(self, key_id: str, private_key_pem: str, method: str, path: str) -> Dict[str, str]:
        timestamp = str(int(time.time()))
        canonical = f"{method}\n{path}\n{timestamp}"
        signature = self._sign_message(private_key_pem, canonical)
        return {
            "Key-Id": key_id,
            "Timestamp": timestamp,
            "Signature": signature,
        }

    def _build_query_items(self, parameters: dict) -> list[Tuple[str, str]]:
        param_map = {
            "ticker": "ticker",
            "eventTicker": "event_ticker",
            "status": "status",
            "minTs": "min_ts",
            "maxTs": "max_ts",
            "subaccount": "subaccount",
            "limit": "limit",
            "cursor": "cursor",
        }
        query_items = []
        for py_key, query_key in param_map.items():
            value = parameters.get(py_key)
            if value:
                query_items.append((query_key, str(value)))
        return query_items

    def _transform_orders(self, raw_orders: list[dict]) -> list[dict]:
        orders = []
        for order in raw_orders:
            o = {
                "order_id": order.get("order_id"),
                "user_id": order.get("user_id"),
                "client_order_id": order.get("client_order_id"),
                "ticker": order.get("ticker"),
                "side": order.get("side"),
                "action": order.get("action"),
                "type": order.get("type"),
                "status": order.get("status"),
                "yes_price": order.get("yes_price"),
                "no_price": order.get("no_price"),
                "yes_price_dollars": order.get("yes_price_dollars"),
                "no_price_dollars": order.get("no_price_dollars"),
                "fill_count": order.get("fill_count"),
                "fill_count_fp": order.get("fill_count_fp"),
                "remaining_count": order.get("remaining_count"),
                "remaining_count_fp": order.get("remaining_count_fp"),
                "initial_count": order.get("initial_count"),
                "initial_count_fp": order.get("initial_count_fp"),
                "taker_fees": order.get("taker_fees"),
                "maker_fees": order.get("maker_fees"),
                "taker_fees_dollars": order.get("taker_fees_dollars"),
                "maker_fees_dollars": order.get("maker_fees_dollars"),
                "taker_fill_cost": order.get("taker_fill_cost"),
                "maker_fill_cost": order.get("maker_fill_cost"),
                "taker_fill_cost_dollars": order.get("taker_fill_cost_dollars"),
                "maker_fill_cost_dollars": order.get("maker_fill_cost_dollars"),
                "queue_position": order.get("queue_position"),
                "expiration_time": order.get("expiration_time"),
                "created_time": order.get("created_time"),
                "last_update_time": order.get("last_update_time"),
                "self_trade_prevention_type": order.get("self_trade_prevention_type"),
                "order_group_id": order.get("order_group_id"),
                "cancel_order_on_pause": order.get("cancel_order_on_pause"),
            }
            orders.append(o)
        return orders

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Filter by market ticker (e.g., \"KXBTC-24DEC31\")",
                },
                "eventTicker": {
                    "type": "string",
                    "description": "Filter by event ticker, max 10 comma-separated (e.g., \"KXBTC-24DEC31,INX-25JAN03\")",
                },
                "status": {
                    "type": "string",
                    "description": "Filter by order status: \"resting\", \"canceled\", or \"executed\"",
                },
                "minTs": {
                    "type": "string",
                    "description": "Minimum timestamp filter (Unix timestamp, e.g., \"1704067200\")",
                },
                "maxTs": {
                    "type": "string",
                    "description": "Maximum timestamp filter (Unix timestamp, e.g., \"1704153600\")",
                },
                "subaccount": {
                    "type": "string",
                    "description": "Subaccount identifier to filter orders",
                },
                "limit": {
                    "type": "string",
                    "description": "Number of results to return (1-200, default: 100)",
                },
                "cursor": {
                    "type": "string",
                    "description": "Pagination cursor from previous response for fetching next page",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        key_id, private_key_pem = self._get_credentials(context)
        if self._is_placeholder_token(key_id or "") or self._is_placeholder_token(private_key_pem or ""):
            return ToolResult(success=False, output="", error="Kalshi credentials not configured.")

        base_path = "/trade-api/v2/portfolio/orders"
        base_url = "https://trade-api.kalshi.com"
        query_items = self._build_query_items(parameters)
        if query_items:
            query_string = urlencode(query_items)
            url = f"{base_url}{base_path}?{query_string}"
        else:
            url = f"{base_url}{base_path}"

        headers = self._get_auth_headers(key_id, private_key_pem, "GET", base_path)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code in [200]:
                    data = response.json()
                    raw_orders = data.get("orders", [])
                    orders = self._transform_orders(raw_orders)
                    cursor = data.get("cursor")
                    output_data = {
                        "orders": orders,
                        "cursor": cursor,
                    }
                    return ToolResult(success=True, output=str(output_data), data=output_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")