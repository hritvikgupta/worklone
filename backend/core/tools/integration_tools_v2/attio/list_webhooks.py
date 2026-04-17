from typing import Any, Dict, List
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class AttioListWebhooksTool(BaseTool):
    name = "attio_list_webhooks"
    description = "List all webhooks in the Attio workspace"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="ATTIO_ACCESS_TOKEN",
                description="Attio access token",
                env_var="ATTIO_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "attio",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("ATTIO_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "number",
                    "description": "Maximum number of webhooks to return",
                },
                "offset": {
                    "type": "number",
                    "description": "Number of webhooks to skip for pagination",
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
        }
        
        url = "https://api.attio.com/v2/webhooks"
        params: Dict[str, Any] = {}
        if parameters.get("limit") is not None:
            params["limit"] = parameters["limit"]
        if parameters.get("offset") is not None:
            params["offset"] = parameters["offset"]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params)
                
                if response.status_code == 200:
                    raw_data = response.json()
                    webhooks: List[Dict[str, Any]] = []
                    data_list = raw_data.get("data", [])
                    for w in data_list:
                        webhook_id = w.get("id", {}).get("webhook_id")
                        subscriptions_raw = w.get("subscriptions", [])
                        subscriptions = [
                            {
                                "eventType": s.get("event_type"),
                                "filter": s.get("filter"),
                            }
                            for s in subscriptions_raw
                        ]
                        webhook = {
                            "webhookId": webhook_id,
                            "targetUrl": w.get("target_url"),
                            "subscriptions": subscriptions,
                            "status": w.get("status"),
                            "createdAt": w.get("created_at"),
                        }
                        webhooks.append(webhook)
                    transformed = {
                        "webhooks": webhooks,
                        "count": len(webhooks),
                    }
                    return ToolResult(
                        success=True, output=json.dumps(transformed), data=transformed
                    )
                else:
                    error_msg = response.text
                    try:
                        err_data = response.json()
                        if isinstance(err_data, dict):
                            error_msg = err_data.get("message") or error_msg
                    except:
                        pass
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")