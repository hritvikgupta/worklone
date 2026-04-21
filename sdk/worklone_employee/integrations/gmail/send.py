from typing import Any, Dict, List, Optional
import base64
import httpx
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class GmailSendTool(BaseTool):
    name = "gmail_send"
    description = "Send emails using Gmail"
    category = "integration"

    GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GOOGLE_ACCESS_TOKEN",
                description="Access token for Gmail API",
                env_var="GOOGLE_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "google",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("GOOGLE_ACCESS_TOKEN",),
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
                                "description": "File name",
                            },
                            "mimeType": {
                                "type": "string",
                                "description": "MIME type (default: application/octet-stream)",
                            },
                            "content": {
                                "type": "string",
                                "description": "Base64-encoded file content",
                            },
                        },
                        "required": ["filename", "content"],
                    },
                    "description": "Files to attach to the email",
                },
            },
            "required": ["to", "body"],
        }

    async def _fetch_threading_headers(self, message_id: str, access_token: str) -> Dict[str, Optional[str]]:
        url = f"{self.GMAIL_API_BASE}/messages/{message_id}"
        params = {
            "format": "metadata",
            "metadataHeaders": "Message-ID,References,Subject",
        }
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            payload_headers = data.get("payload", {}).get("headers", [])
            headers_dict = {h["name"]: h["value"] for h in payload_headers}
            return {
                "messageId": headers_dict.get("Message-ID"),
                "references": headers_dict.get("References"),
                "subject": headers_dict.get("Subject"),
            }

    def _base64url_encode(self, data: str) -> str:
        encoded = base64.urlsafe_b64encode(data.encode("utf-8"))
        return encoded.decode("utf-8").rstrip("=")

    def _build_simple_message(
        self,
        to: str,
        cc: Optional[str],
        bcc: Optional[str],
        subject: str,
        body: str,
        content_type: str,
        in_reply_to: Optional[str] = None,
        references: Optional[str] = None,
    ) -> str:
        msg = MIMEText(body, content_type, "utf-8")
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
        return msg.as_string()

    def _build_message_with_attachments(
        self,
        to: str,
        cc: Optional[str],
        bcc: Optional[str],
        subject: str,
        body: str,
        content_type: str,
        attachments: List[Dict[str, Any]],
        in_reply_to: Optional[str] = None,
        references: Optional[str] = None,
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
        body_part = MIMEText(body, content_type, "utf-8")
        msg.attach(body_part)
        for att in attachments:
            filename = att["filename"]
            mime_type = att["mimeType"]
            content = att["content"]  # bytes
            part = MIMEBase(*mime_type.split("/", 1))
            part.set_payload(content)
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
            msg.attach(part)
        return msg.as_string()

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        reply_to_message_id = parameters.get("replyToMessageId")
        original_message_id: Optional[str] = None
        original_references: Optional[str] = None
        original_subject: Optional[str] = None
        if reply_to_message_id:
            threading_headers = await self._fetch_threading_headers(reply_to_message_id, access_token)
            original_message_id = threading_headers["messageId"]
            original_references = threading_headers["references"]
            original_subject = threading_headers["subject"]

        subject = parameters.get("subject") or original_subject or ""
        to = parameters["to"]
        body = parameters["body"]
        content_type = parameters.get("contentType", "text")
        cc = parameters.get("cc")
        bcc = parameters.get("bcc")
        thread_id = parameters.get("threadId")
        attachments_list = parameters.get("attachments", [])

        raw_message: str
        if attachments_list:
            attachment_buffers: List[Dict[str, Any]] = []
            total_size = 0
            for att in attachments_list:
                filename = att.get("filename")
                if not filename:
                    return ToolResult(success=False, output="", error="Attachment missing filename")
                mime_type = att.get("mimeType", "application/octet-stream")
                content_b64 = att.get("content")
                if not content_b64:
                    return ToolResult(success=False, output="", error="Attachment missing content")
                try:
                    content = base64.b64decode(content_b64)
                except Exception:
                    return ToolResult(success=False, output="", error="Invalid base64 content in attachment")
                total_size += len(content)
                attachment_buffers.append({"filename": filename, "mimeType": mime_type, "content": content})
            if total_size > 25 * 1024 * 1024:
                size_mb = total_size / (1024 * 1024)
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Total attachment size ({size_mb:.2f}MB) exceeds Gmail's limit of 25MB",
                )
            raw_message = self._build_message_with_attachments(
                to, cc, bcc, subject, body, content_type, attachment_buffers, original_message_id, original_references
            )
        else:
            raw_message = self._build_simple_message(
                to, cc, bcc, subject, body, content_type, original_message_id, original_references
            )

        request_body: Dict[str, Any] = {"raw": self._base64url_encode(raw_message)}
        if thread_id:
            request_body["threadId"] = thread_id

        url = f"{self.GMAIL_API_BASE}/messages/send"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=request_body)

                if response.status_code in [200, 201, 204]:
                    data = response.json() if response.content else {}
                    return ToolResult(success=True, output="Email sent successfully", data=data)
                else:
                    error_text = response.text
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Gmail API error ({response.status_code}): {error_text}",
                    )
        except httpx.HTTPStatusError as e:
            return ToolResult(success=False, output="", error=f"Gmail API error: {str(e)}")
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")