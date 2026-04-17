from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class AttioUpdateWebhookTool(BaseTool):
    name = "attio_update_webhook"
    description = "Update a webhook in Attio (target URL and/or subscriptions)"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="ATTIO_ACCESS_TOKEN",
                description="Access token",
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
                "webhookId": {
                    "type": "string",
                    "description": "The webhook ID to update",
                },
                "targetUrl": {
                    "type": "string",
                    "description": "HTTPS target URL for webhook delivery",
                },
                "subscriptions": {
                    "type": "string",
                    "description": "JSON array of subscriptions, e.g. [{'event_type':'note.created'}]",
                },
            },
            "required": ["webhookId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        webhook_id = (parameters.get("webhookId") or "").strip()
        if not webhook_id:
            return ToolResult(success=False, output="", error="webhookId is required.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = f"https://api.attio.com/v2/webhooks/{webhook_id}"
        
        data: dict[str, Any] = {}
        target_url = parameters.get("targetUrl")
        if target_url:
            data["target_url"] = target_url.strip()
        subscriptions = parameters.get("subscriptions")
        if subscriptions:
            try:
                data["subscriptions"] = json.loads(subscriptions)
            except json.JSONDecodeError:
                data["subscriptions"] = []
        
        json_body = {"data": data}
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(url, headers=headers, json=json_body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")