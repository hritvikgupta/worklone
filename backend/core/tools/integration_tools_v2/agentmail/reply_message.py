from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class AgentmailReplyMessageTool(BaseTool):
    name = "agentmail_reply_message"
    description = "Reply to an existing email message in AgentMail"
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

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "inboxId": {
                    "type": "string",
                    "description": "ID of the inbox to reply from",
                },
                "messageId": {
                    "type": "string",
                    "description": "ID of the message to reply to",
                },
                "text": {
                    "type": "string",
                    "description": "Plain text reply body",
                },
                "html": {
                    "type": "string",
                    "description": "HTML reply body",
                },
                "to": {
                    "type": "string",
                    "description": "Override recipient email addresses (comma-separated)",
                },
                "cc": {
                    "type": "string",
                    "description": "CC email addresses (comma-separated)",
                },
                "bcc": {
                    "type": "string",
                    "description": "BCC email addresses (comma-separated)",
                },
                "replyAll": {
                    "type": "boolean",
                    "description": "Reply to all recipients of the original message",
                },
            },
            "required": ["inboxId", "messageId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("AGENTMAIL_API_KEY") if context else None
        if self._is_placeholder_token(api_key or ""):
            return ToolResult(success=False, output="", error="AgentMail API key not configured.")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        inbox_id = parameters["inboxId"].strip()
        message_id = parameters["messageId"].strip()
        reply_all = parameters.get("replyAll", False)
        endpoint = "reply-all" if reply_all else "reply"
        url = f"https://api.agentmail.to/v0/inboxes/{inbox_id}/messages/{message_id}/{endpoint}"

        body = {}
        text = parameters.get("text")
        if text:
            body["text"] = text
        html = parameters.get("html")
        if html:
            body["html"] = html
        if not reply_all:
            to = parameters.get("to")
            if to:
                body["to"] = [e.strip() for e in str(to).split(",")]
            cc = parameters.get("cc")
            if cc:
                body["cc"] = [e.strip() for e in str(cc).split(",")]
            bcc = parameters.get("bcc")
            if bcc:
                body["bcc"] = [e.strip() for e in str(bcc).split(",")]

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")