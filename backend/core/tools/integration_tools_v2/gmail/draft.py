from typing import Any, Dict, List, Optional
import httpx
import base64
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GmailDraftTool(BaseTool):
    name = "gmail_draft"
    description = "Draft emails using Gmail. Returns API-aligned fields only."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="access_token",
                description="Access token for Gmail API",
                env_var="GMAIL_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "google",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("GMAIL_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def _fetch_threading_headers(self, message_id: str, access_token: str) -> Dict[str, str | None]:
        url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}?format=minimal"
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            payload_headers = data.get("payload", {}).get("headers", [])
            def get_header(name: str) -> str | None:
                for h in payload_headers:
                    if h["name"].lower() == name.lower():
                        return h["value"]
                return None
            return {
                "messageId": get_header("Message-ID"),
                "references": get_header("References"),
                "subject": get_header("Subject"),
            }

    def _build_simple_email_message(
        self,
        to: str,
        cc: Optional[str],
        bcc: Optional[str],
        subject: str,
        body: str,
        content_type: str,
        in_reply_to: Optional[str],
        references: Optional[str],
    ) -> str:
        msg = EmailMessage()
        msg["To"] = to
        if cc:
            msg["Cc"] = cc
        if bcc:
            msg["Bcc"] = bcc
        msg["Subject"] = subject
        if in_reply_to:
            msg["In-Reply-To"] = in_reply_to
        if references:
            msg["References"] = references
        msg.set_content(body, subtype=content_type)
        return msg.as_string()

    def _build_mime_message(
        self,
        to: str,
        cc: Optional[str],
        bcc: Optional[str],
        subject: str,
        body: str,
        content_type: str,
        in_reply_to: Optional[str],
        references: Optional[str],
        attachments: List[Dict[str, Any]],
    ) -> str:
        msg = MIMEMultipart("mixed")
        msg["To"] = to
        if cc:
            msg["Cc"] = cc
        if bcc:
            msg["Bcc"] = bcc
        msg["Subject"] = subject
        if in_reply_to:
            msg["In-Reply-To"] = in_reply_to
        if references:
            msg["References"] = references
        body_part = MIMEText(body, content_type)
        msg.attach(body_part)
        for att in attachments:
            content = att["content"]  # bytes
            mime_type = att["mimeType"]
            filename = att["filename"]
            sub_type = mime_type.split("/", 1)[1] if "/" in mime_type else "octet-stream"
            att_part = MIMEApplication(content, _subtype=sub_type)
            att_part.add_header("Content-Disposition", "attachment", filename=filename)
            att_part.add_header("Content-Type", mime_type)
            msg.attach(att_part)
        return msg.as_string()

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "to": {
                    "type": "string",
                    "description": "Recipient email address",
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
                "threadId": {
                    "type": "string",
                    "description": "Thread ID to reply to (for threading)",
                },
                "replyToMessageId": {
                    "type": "string",
                    "description": 'Gmail message ID to reply to - use the "id" field from Gmail Read results (not the RFC "messageId")',
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
                    "items": {
                        "type": "object",
                        "properties": {
                            "filename": {
                                "type": "string",
                                "description": "Attachment filename",
                            },
                            "mimeType": {
                                "type": "string",
                                "description": "MIME type of the attachment",
                            },
                            "data": {
                                "type": "string",
                                "description": "Base64-encoded content of the file",
                            },
                        },
                        "required": ["filename", "data"],
                    },
                    "description": "Files to attach to the email draft",
                },
            },
            "required": ["to", "body"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        params = parameters
        to = params["to"]
        subject = params.get("subject", "")
        body = params["body"]
        content_type = params.get("contentType", "text")
        thread_id = params.get("threadId")
        reply_to_message_id = params.get("replyToMessageId")
        cc = params.get("cc")
        bcc = params.get("bcc")
        attachments_input = params.get("attachments", [])

        original_message_id = None
        original_references = None
        original_subject = None
        if reply_to_message_id:
            threading_headers = self._fetch_threading_headers(reply_to_message_id, access_token)
            original_message_id = threading_headers.get("messageId")
            original_references = threading_headers.get("references")
            original_subject = threading_headers.get("subject")

        if not subject:
            subject = original_subject or ""

        attachment_parts: List[Dict[str, Any]] = []
        total_size = 0
        if attachments_input:
            for att in attachments_input:
                filename = att.get("filename") or att.get("name")
                if not filename:
                    return ToolResult(success=False, output="", error="All attachments must have a filename")
                mime_type = att.get("mimeType", "application/octet-stream")
                data_b64 = att.get("data") or att.get("content")
                if not data_b64:
                    return ToolResult(success=False, output="", error=f"Attachment {filename} missing data")
                try:
                    content = base64.b64decode(data_b64)
                    size = len(content)
                    if total_size + size > 25 * 1024 * 1024:
                        return ToolResult(success=False, output="", error="Total attachment size exceeds Gmail's limit of 25MB")
                    total_size += size
                    attachment_parts.append({
                        "filename": filename,
                        "mimeType": mime_type,
                        "content": content,
                    })
                except Exception as e:
                    return ToolResult(success=False, output="", error=f"Failed to process attachment {filename}: {str(e)}")

        if attachment_parts:
            raw_message = self._build_mime_message(
                to, cc, bcc, subject, body, content_type,
                original_message_id, original_references, attachment_parts
            )
        else:
            raw_message = self._build_simple_email_message(
                to, cc, bcc, subject, body, content_type,
                original_message_id, original_references
            )

        raw_message_b64 = base64.urlsafe_b64encode(raw_message.encode("utf-8")).decode("ascii").rstrip("=")

        draft_body = {
            "message": {"raw": raw_message_b64}
        }
        if thread_id:
            draft_body["message"]["threadId"] = thread_id

        url = "https://gmail.googleapis.com/gmail/v1/users/me/drafts"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=draft_body)
                
                if response.status_code in [200, 201]:
                    data = response.json()
                    output_data = {
                        "draftId": data.get("id"),
                        "messageId": data.get("message", {}).get("id"),
                        "threadId": data.get("message", {}).get("threadId"),
                        "labelIds": data.get("message", {}).get("labelIds"),
                    }
                    return ToolResult(
                        success=True,
                        output="Email drafted successfully.",
                        data=output_data
                    )
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")