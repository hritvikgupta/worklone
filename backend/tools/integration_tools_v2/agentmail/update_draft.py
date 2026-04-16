from typing import Any, Dict
import httpx
import os
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class AgentmailUpdateDraftTool(BaseTool):
    name = "agentmail_update_draft"
    description = "Update an existing email draft in AgentMail"
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

    def _resolve_api_key(self, context: dict | None) -> str:
        api_key = context.get("AGENTMAIL_API_KEY") if context else None
        if api_key is None:
            api_key = os.getenv("AGENTMAIL_API_KEY")
        return api_key or ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "inboxId": {
                    "type": "string",
                    "description": "ID of the inbox containing the draft",
                },
                "draftId": {
                    "type": "string",
                    "description": "ID of the draft to update",
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
                "sendAt": {
                    "type": "string",
                    "description": "ISO 8601 timestamp to schedule sending",
                },
            },
            "required": ["inboxId", "draftId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = self._resolve_api_key(context)
        
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="API key not configured.")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        inbox_id = parameters["inboxId"].strip()
        draft_id = parameters["draftId"].strip()
        url = f"https://api.agentmail.to/v0/inboxes/{inbox_id}/drafts/{draft_id}"
        
        body = {}
        to = parameters.get("to")
        if to:
            body["to"] = [e.strip() for e in to.split(",")]
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
            body["cc"] = [e.strip() for e in cc.split(",")]
        bcc = parameters.get("bcc")
        if bcc:
            body["bcc"] = [e.strip() for e in bcc.split(",")]
        send_at = parameters.get("sendAt")
        if send_at:
            body["send_at"] = send_at
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")