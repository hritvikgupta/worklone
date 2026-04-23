from typing import Any, Dict, List
import base64
import httpx
from datetime import datetime
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class OutlookSendTool(BaseTool):
    name = "outlook_send"
    description = "Send emails using Outlook"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="OUTLOOK_ACCESS_TOKEN",
                description="Access token for Outlook API",
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
                "to": {
                    "type": "string",
                    "description": "Recipient email address (comma-separated for multiple recipients)",
                },
                "subject": {
                    "type": "string",
                    "description": "Email subject",
                },
                "body": {
                    "type": "string",
                    "description": "Email body content",
                },
                "contentType": {
                    "type": "string",
                    "description": "Content type for the email body (text or html)",
                },
                "replyToMessageId": {
                    "type": "string",
                    "description": "Message ID to reply to (for threading)",
                },
                "conversationId": {
                    "type": "string",
                    "description": "Conversation ID for threading",
                },
                "cc": {
                    "type": "string",
                    "description": "CC recipients (comma-separated)",
                },
                "bcc": {
                    "type": "string",
                    "description": "BCC recipients (comma-separated)",
                },
                "attachments": {
                    "type": "array",
                    "items": {"type": "file"},
                    "description": "Files to attach to the email",
                },
            },
            "required": ["to", "subject", "body"],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        to = parameters["to"]
        subject = parameters["subject"]
        body = parameters["body"]
        content_type = parameters.get("contentType", "text")
        cc = parameters.get("cc")
        bcc = parameters.get("bcc")
        reply_to_message_id = parameters.get("replyToMessageId")
        attachments_input: List[Dict[str, Any]] = parameters.get("attachments", [])

        to_emails = [e.strip() for e in to.split(",") if e.strip()]
        to_recipient = [{"emailAddress": {"address": email}} for email in to_emails]

        cc_recipients = None
        if cc:
            cc_emails = [e.strip() for e in cc.split(",") if e.strip()]
            cc_recipient = [{"emailAddress": {"address": email}} for email in cc_emails]
            if cc_emails:
                cc_recipients = cc_recipient

        bcc_recipient = None
        if bcc:
            bcc_emails = [e.strip() for e in bcc.split(",") if e.strip()]
            bcc_recipients = [{"emailAddress": {"address": email}} for email in bcc_emails]
            if bcc_emails:
                bcc_recipient = bcc_recipient

        message: Dict[str, Any] = {
            "subject": subject,
            "body": {
                "contentType": content_type,
                "content": body,
            },
            "toRecipients": to_recipient,
        }
        if cc_recipients is not None:
            message["ccRecipients"] = cc_recipient
        if bcc_recipient is not None:
            message["bccRecipients"] = bcc_recipient

        attachment_objects: List[Dict[str, Any]] = []
        if attachments_input:
            total_size = sum(int(att.get("size", 0)) for att in attachments_input)
            max_size = 3 * 1024 * 1024
            if total_size > max_size:
                size_mb = total_size / (1024 * 1024)
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Total attachment size ({size_mb:.2f}MB) exceeds Microsoft Graph API limit of 3MB per request",
                )

        url = (
            f"https://graph.microsoft.com/v1.0/me/messages/{reply_to_message_id}/reply"
            if reply_to_message_id
            else "https://graph.microsoft.com/v1.0/me/sendMail"
        )

        request_body = (
            {
                "comment": body,
                "message": message,
            }
            if reply_to_message_id
            else {
                "message": message,
                "saveToSentItems": True,
            }
        )

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if attachments_input:
                    for att in attachments_input:
                        att_url = att.get("url")
                        if not att_url:
                            return ToolResult(
                                success=False,
                                output="",
                                error=f"Attachment missing URL: {att.get('name', 'unknown')}",
                            )
                        resp = await client.get(att_url, timeout=30.0)
                        resp.raise_for_status()
                        content = resp.content
                        base64_content = base64.b64encode(content).decode("utf-8")
                        attachment_obj = {
                            "@odata.type": "#microsoft.graph.fileAttachment",
                            "name": att["name"],
                            "contentType": att.get("type", "application/octet-stream"),
                            "contentBytes": base64_content,
                        }
                        attachment_objects.append(attachment_obj)
                    if attachment_objects:
                        message["attachments"] = attachment_objects

                response = await client.post(url, headers=headers, json=request_body)

                if response.status_code in [200, 201, 202, 204]:
                    timestamp = datetime.now().isoformat()
                    attachment_count = len(attachment_objects)
                    output_data = {
                        "message": "Email sent successfully",
                        "status": "sent",
                        "timestamp": timestamp,
                        "attachmentCount": attachment_count,
                    }
                    return ToolResult(
                        success=True,
                        output="Email sent successfully",
                        data=output_data,
                    )
                else:
                    try:
                        error_data = response.json()
                        error_msg = (
                            error_data.get("error", {}).get("message", "")
                            or error_data.get("error", "Failed to send email")
                        )
                    except Exception:
                        error_msg = response.text or "Failed to send email"
                    return ToolResult(success=False, output="", error=error_msg)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")