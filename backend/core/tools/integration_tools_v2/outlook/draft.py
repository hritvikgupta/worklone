from typing import Any, Dict
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class OutlookDraftTool(BaseTool):
    name = "outlook_draft"
    description = "Draft emails using Outlook"
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
            context_token_keys=("provider_token",),
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
                    "enum": ["text", "html"],
                    "description": "Content type for the email body (text or html)",
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
                            "name": {"type": "string", "description": "File name"},
                            "url": {"type": "string", "description": "Download URL for the file"},
                            "contentType": {"type": "string", "description": "MIME type"},
                            "size": {"type": "number", "description": "File size in bytes"},
                        },
                        "required": ["name", "url"],
                    },
                    "description": "Files to attach to the email draft",
                },
            },
            "required": ["to", "subject", "body"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = "https://graph.microsoft.com/v1.0/me/messages"
        
        to_str = parameters["to"]
        to_emails = [e.strip() for e in to_str.split(",") if e.strip()]
        if not to_emails:
            return ToolResult(success=False, output="", error="No valid 'to' recipients provided.")
        
        message: dict = {
            "subject": parameters["subject"],
            "body": {
                "contentType": parameters.get("contentType", "text"),
                "content": parameters["body"],
            },
            "toRecipients": [{"emailAddress": {"address": email}} for email in to_emails],
        }
        
        cc_str = parameters.get("cc")
        if cc_str:
            cc_emails = [e.strip() for e in cc_str.split(",") if e.strip()]
            if cc_emails:
                message["ccRecipients"] = [{"emailAddress": {"address": email}} for email in cc_emails]
        
        bcc_str = parameters.get("bcc")
        if bcc_str:
            bcc_emails = [e.strip() for e in bcc_str.split(",") if e.strip()]
            if bcc_emails:
                message["bccRecipients"] = [{"emailAddress": {"address": email}} for email in bcc_emails]
        
        attachments = parameters.get("attachments", [])
        if attachments:
            attachment_objects = []
            total_size = 0
            for file_info in attachments:
                name = file_info.get("name")
                if not name:
                    return ToolResult(success=False, output="", error="Attachment missing 'name'.")
                url_att = file_info.get("url")
                if not url_att:
                    return ToolResult(success=False, output="", error=f"Attachment '{name}' missing 'url'.")
                content_type = file_info.get("contentType", "application/octet-stream")
                try:
                    async with httpx.AsyncClient(timeout=30.0) as dl_client:
                        file_resp = await dl_client.get(url_att)
                        file_resp.raise_for_status()
                        content_bytes = file_resp.content
                        total_size += len(content_bytes)
                        if total_size > 4 * 1024 * 1024:
                            return ToolResult(
                                success=False,
                                output="",
                                error=f"Total attachment size ({total_size / (1024 * 1024):.2f}MB) exceeds 4MB limit.",
                            )
                        b64_content = base64.b64encode(content_bytes).decode("utf-8")
                        attachment_objects.append(
                            {
                                "@odata.type": "#microsoft.graph.fileAttachment",
                                "name": name,
                                "contentType": content_type,
                                "contentBytes": b64_content,
                            }
                        )
                except httpx.HTTPStatusError as e:
                    return ToolResult(
                        success=False, output="", error=f"Failed to download attachment '{name}': {e.response.status_code} - {e.response.text}"
                    )
                except Exception as dl_err:
                    return ToolResult(
                        success=False, output="", error=f"Failed to process attachment '{name}': {str(dl_err)}"
                    )
            if attachment_objects:
                message["attachments"] = attachment_objects
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=message)
                
                if response.status_code in [200, 201]:
                    data = response.json()
                    return ToolResult(success=True, output=response.text, data=data)
                else:
                    try:
                        error_data = response.json()
                    except:
                        error_data = {}
                    error_msg = (
                        error_data.get("error", {}).get("message", response.text)
                        if error_data
                        else response.text
                    )
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")