from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class OutlookForwardTool(BaseTool):
    name = "outlook_forward"
    description = "Forward an existing Outlook message to specified recipients"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="OUTLOOK_ACCESS_TOKEN",
                description="OAuth access token for Outlook",
                env_var="OUTLOOK_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "outlook",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("OUTLOOK_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "messageId": {
                    "type": "string",
                    "description": "The ID of the message to forward",
                },
                "to": {
                    "type": "string",
                    "description": "Recipient email address(es), comma-separated",
                },
                "comment": {
                    "type": "string",
                    "description": "Optional comment to include with the forwarded message",
                },
            },
            "required": ["messageId", "to"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        message_id = parameters["messageId"]
        to_str = parameters["to"]
        
        if not to_str or not to_str.strip():
            return ToolResult(success=False, output="", error="At least one recipient is required to forward a message")
        
        emails = [email.strip() for email in to_str.split(",") if email.strip()]
        if not emails:
            return ToolResult(success=False, output="", error="At least one recipient is required to forward a message")
        
        to_recipients = [{"emailAddress": {"address": email}} for email in emails]
        
        comment = parameters.get("comment", "")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = f"https://graph.microsoft.com/v1.0/me/messages/{message_id}/forward"
        body = {
            "comment": comment,
            "toRecipients": to_recipient,
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 202, 204]:
                    try:
                        return ToolResult(success=True, output=response.text, data=response.json())
                    except:
                        return ToolResult(success=True, output=response.text or "Email forwarded successfully", data={})
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")