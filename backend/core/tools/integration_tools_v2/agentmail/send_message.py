from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class AgentmailSendMessageTool(BaseTool):
    name = "agentmail_send_message"
    description = "Send an email message from an AgentMail inbox"
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
        if context is None:
            return ""
        return context.get("AGENTMAIL_API_KEY", "")

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "inboxId": {
                    "type": "string",
                    "description": "ID of the inbox to send from",
                },
                "to": {
                    "type": "string",
                    "description": "Recipient email address (comma-separated for multiple)",
                },
                "subject": {
                    "type": "string",
                    "description": "Email subject line",
                },
                "text": {
                    "type": "string",
                    "description": "Plain text email body",
                },
                "html": {
                    "type": "string",
                    "description": "HTML email body",
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
            "required": ["inboxId", "to", "subject"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        url = f"https://api.agentmail.to/v0/inboxes/{parameters['inboxId'].strip()}/messages/send"

        body: Dict[str, Any] = {
            "to": [e.strip() for e in parameters["to"].split(",")],
            "subject": parameters["subject"],
        }
        if parameters.get("text"):
            body["text"] = parameters["text"]
        if parameters.get("html"):
            body["html"] = parameters["html"]
        if parameters.get("cc"):
            body["cc"] = [e.strip() for e in parameters["cc"].split(",")]
        if parameters.get("bcc"):
            body["bcc"] = [e.strip() for e in parameters["bcc"].split(",")]

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")