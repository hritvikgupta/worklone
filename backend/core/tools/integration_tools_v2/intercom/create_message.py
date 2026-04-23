from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class IntercomCreateMessageTool(BaseTool):
    name = "intercom_create_message"
    description = "Create and send a new admin-initiated message in Intercom. Returns API-aligned fields only."
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
            context_token_keys=("access_token",),
            env_token_keys=("INTERCOM_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "message_type": {
                    "type": "string",
                    "description": 'Message type: "inapp" for in-app messages or "email" for email messages',
                },
                "template": {
                    "type": "string",
                    "description": 'Message template style: "plain" for plain text or "personal" for personalized style',
                },
                "subject": {
                    "type": "string",
                    "description": "The subject of the message (for email type)",
                },
                "body": {
                    "type": "string",
                    "description": "The body of the message",
                },
                "from_type": {
                    "type": "string",
                    "description": 'Sender type: "admin"',
                },
                "from_id": {
                    "type": "string",
                    "description": "The ID of the admin sending the message",
                },
                "to_type": {
                    "type": "string",
                    "description": 'Recipient type: "contact"',
                },
                "to_id": {
                    "type": "string",
                    "description": "The ID of the contact receiving the message",
                },
                "created_at": {
                    "type": "number",
                    "description": "Unix timestamp for when the message was created. If not provided, current time is used.",
                },
            },
            "required": [
                "message_type",
                "template",
                "body",
                "from_type",
                "from_id",
                "to_type",
                "to_id",
            ],
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
        
        url = "https://api.intercom.io/messages"
        
        api_message_type = "in_app" if parameters["message_type"] == "inapp" else parameters["message_type"]
        body = {
            "message_type": api_message_type,
            "template": parameters["template"],
            "body": parameters["body"],
            "from": {
                "type": parameters["from_type"],
                "id": parameters["from_id"],
            },
            "to": {
                "type": parameters["to_type"],
                "id": parameters["to_id"],
            },
        }
        if parameters.get("subject") and parameters["message_type"] == "email":
            body["subject"] = parameters["subject"]
        if "created_at" in parameters:
            body["created_at"] = parameters["created_at"]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")