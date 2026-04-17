from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class AgentMailForwardMessageTool(BaseTool):
    name = "agentmail_forward_message"
    description = "Forward an email message to new recipients in AgentMail"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="AGENTMAIL_API_KEY",
                description="AgentMail API key",
                env_var="AGENTMAIL_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "agentmail",
            context=context,
            context_token_keys=("agentmail_api_key",),
            env_token_keys=("AGENTMAIL_API_KEY",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "inboxId": {
                    "type": "string",
                    "description": "ID of the inbox containing the message",
                },
                "messageId": {
                    "type": "string",
                    "description": "ID of the message to forward",
                },
                "to": {
                    "type": "string",
                    "description": "Recipient email addresses (comma-separated)",
                },
                "subject": {
                    "type": "string",
                    "description": "Override subject line",
                },
                "text": {
                    "type": "string",
                    "description": "Additional plain text to prepend",
                },
                "html": {
                    "type": "string",
                    "description": "Additional HTML to prepend",
                },
                "cc": {
                    "type": "string",
                    "description": "CC recipient email addresses (comma-separated)",
                },
                "bcc": {
                    "type": "string",
                    "description": "BCC recipient email addresses (comma-separated)",
                },
            },
            "required": ["inboxId", "messageId", "to"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = f"https://api.agentmail.to/v0/inboxes/{parameters['inboxId'].strip()}/messages/{parameters['messageId'].strip()}/forward"
        
        body: Dict[str, Any] = {
            "to": [e.strip() for e in parameters["to"].split(",")],
        }
        for field in ["subject", "text", "html"]:
            if field in parameters and parameters[field]:
                body[field] = parameters[field]
        for field in ["cc", "bcc"]:
            if field in parameters and parameters[field]:
                body[field] = [e.strip() for e in parameters[field].split(",")]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")