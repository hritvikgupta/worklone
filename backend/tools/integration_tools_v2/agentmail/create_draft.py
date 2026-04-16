from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class AgentmailCreateDraftTool(BaseTool):
    name = "agentmail_create_draft"
    description = "Create a new email draft in AgentMail"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="apiKey",
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
            context_token_keys=("apiKey",),
            env_token_keys=("AGENTMAIL_API_KEY",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "apiKey": {
                    "type": "string",
                    "description": "AgentMail API key",
                },
                "inboxId": {
                    "type": "string",
                    "description": "ID of the inbox to create the draft in",
                },
                "to": {
                    "type": "string",
                    "description": "Recipient email addresses (comma-separated)",
                },
                "subject": {
                    "type": "string",
                    "description": "Draft subject line",
                },
                "text": {
                    "type": "string",
                    "description": "Plain text draft body",
                },
                "html": {
                    "type": "string",
                    "description": "HTML draft body",
                },
                "cc": {
                    "type": "string",
                    "description": "CC recipient email addresses (comma-separated)",
                },
                "bcc": {
                    "type": "string",
                    "description": "BCC recipient email addresses (comma-separated)",
                },
                "inReplyTo": {
                    "type": "string",
                    "description": "ID of message being replied to",
                },
                "sendAt": {
                    "type": "string",
                    "description": "ISO 8601 timestamp to schedule sending",
                },
            },
            "required": ["apiKey", "inboxId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        inbox_id = parameters["inboxId"].strip()
        url = f"https://api.agentmail.to/v0/inboxes/{inbox_id}/drafts"
        
        body: dict = {}
        to = parameters.get("to")
        if to:
            body["to"] = [e.strip() for e in str(to).split(",")]
        subject = parameters.get("subject")
        if subject:
            body["subject"] = subject
        text = parameters.get("text")
        if text:
            body["text"] = text
        html = parameters.get("html")
        if html:
            body["html"] = html
        cc = parameters.get("cc")
        if cc:
            body["cc"] = [e.strip() for e in str(cc).split(",")]
        bcc = parameters.get("bcc")
        if bcc:
            body["bcc"] = [e.strip() for e in str(bcc).split(",")]
        in_reply_to = parameters.get("inReplyTo")
        if in_reply_to:
            body["in_reply_to"] = in_reply_to
        send_at = parameters.get("sendAt")
        if send_at:
            body["send_at"] = send_at
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if 200 <= response.status_code < 300:
                    try:
                        data = response.json()
                    except:
                        data = response.text
                    return ToolResult(success=True, output=response.text, data=data)
                else:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("message", "Failed to create draft")
                    except:
                        error_msg = response.text
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")