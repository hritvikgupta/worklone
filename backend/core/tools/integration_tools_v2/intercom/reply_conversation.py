from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class IntercomReplyConversationTool(BaseTool):
    name = "intercom_reply_conversation"
    description = "Reply to a conversation as an admin in Intercom"
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
            context_token_keys=("accessToken",),
            env_token_keys=("INTERCOM_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "conversationId": {
                    "type": "string",
                    "description": "Conversation ID to reply to",
                },
                "message_type": {
                    "type": "string",
                    "description": 'Message type: "comment" or "note"',
                },
                "body": {
                    "type": "string",
                    "description": "The text body of the reply",
                },
                "admin_id": {
                    "type": "string",
                    "description": 'The ID of the admin authoring the reply. If not provided, a default admin (Operator/Fin) will be used.',
                },
                "attachment_urls": {
                    "type": "string",
                    "description": "Comma-separated list of image URLs (max 10)",
                },
                "created_at": {
                    "type": "number",
                    "description": "Unix timestamp for when the reply was created. If not provided, current time is used.",
                },
            },
            "required": ["conversationId", "message_type", "body"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Intercom-Version": "2.14",
        }
        
        conversation_id = parameters["conversationId"]
        url = f"https://api.intercom.io/conversations/{conversation_id}/reply"
        
        body = {
            "message_type": parameters["message_type"],
            "type": "admin",
            "body": parameters["body"],
        }
        
        admin_id = parameters.get("admin_id")
        if admin_id:
            body["admin_id"] = admin_id
        
        attachment_urls = parameters.get("attachment_urls")
        if attachment_urls:
            body["attachment_urls"] = [url.strip() for url in attachment_urls.split(",")][:10]
        
        created_at = parameters.get("created_at")
        if created_at is not None:
            body["created_at"] = created_at
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")