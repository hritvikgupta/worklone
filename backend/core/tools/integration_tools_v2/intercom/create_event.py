from typing import Any, Dict
import httpx
import base64
import time
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class IntercomCreateEventTool(BaseTool):
    name = "intercom_create_event"
    description = "Track a custom event for a contact in Intercom"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="INTERCOM_ACCESS_TOKEN",
                description="Intercom API access token",
                env_var="INTERCOM_ACCESS_TOKEN",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "intercom",
            context=context,
            context_token_keys=("intercom_token",),
            env_token_keys=("INTERCOM_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "event_name": {
                    "type": "string",
                    "description": 'The name of the event (e.g., "order-completed"). Use past-tense verb-noun format for readability.',
                },
                "created_at": {
                    "type": "number",
                    "description": "Unix timestamp for when the event occurred. Strongly recommended for uniqueness.",
                },
                "user_id": {
                    "type": "string",
                    "description": "Your identifier for the user (external_id)",
                },
                "email": {
                    "type": "string",
                    "description": "Email address of the user. Use only if your app uses email to uniquely identify users.",
                },
                "id": {
                    "type": "string",
                    "description": "The Intercom contact ID",
                },
                "metadata": {
                    "type": "string",
                    "description": 'JSON object with up to 10 metadata key-value pairs about the event (e.g., {"order_value": 99.99})',
                },
            },
            "required": ["event_name"],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Intercom-Version": "2.14",
        }
        
        body = {
            "event_name": parameters["event_name"],
        }
        
        created_at = parameters.get("created_at")
        if created_at is not None:
            body["created_at"] = int(created_at)
        else:
            body["created_at"] = int(time.time())
        
        user_id = parameters.get("user_id")
        if user_id:
            body["user_id"] = user_id
        
        email = parameters.get("email")
        if email:
            body["email"] = email
        
        contact_id = parameters.get("id")
        if contact_id:
            body["id"] = contact_id
        
        metadata_str = parameters.get("metadata")
        if metadata_str:
            try:
                body["metadata"] = json.loads(metadata_str)
            except json.JSONDecodeError:
                pass
        
        url = "https://api.intercom.io/events"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 202, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")