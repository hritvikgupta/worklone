"""
Gmail Tool — Read and send emails.
"""

from typing import Any
import httpx
import os
import base64
from backend.workflows.tools.base import BaseTool, ToolResult, CredentialRequirement


class GmailTool(BaseTool):
    """Read and send emails via Gmail API."""
    
    name = "gmail"
    description = "Send or read emails via Gmail API. Use for email notifications, checking inbox, or sending messages."
    category = "communication"
    
    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GMAIL_ACCESS_TOKEN",
                description="Google OAuth2 access token for Gmail API (read and send emails)",
                env_var="GMAIL_ACCESS_TOKEN",
                required=True,
                example="ya29.a0AfH6SM...",
                auth_type="oauth",
                auth_url="https://accounts.google.com/o/oauth2/v2/auth",
                auth_provider="google",
                auth_scopes="https://www.googleapis.com/auth/gmail.modify https://www.googleapis.com/auth/gmail.send",
            ),
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action to perform: 'send', 'list', 'read'",
                    "enum": ["send", "list", "read"],
                },
                "to": {
                    "type": "string",
                    "description": "Recipient email (for 'send' action)",
                },
                "subject": {
                    "type": "string",
                    "description": "Email subject (for 'send' action)",
                },
                "body": {
                    "type": "string",
                    "description": "Email body (for 'send' action)",
                },
                "query": {
                    "type": "string",
                    "description": "Search query (for 'list' action)",
                },
                "message_id": {
                    "type": "string",
                    "description": "Message ID (for 'read' action)",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Max results to return (for 'list' action)",
                },
            },
            "required": ["action"],
        }
    
    async def execute(
        self,
        parameters: dict,
        context: dict = None,
    ) -> ToolResult:
        action = parameters.get("action")
        
        access_token = os.getenv("GMAIL_ACCESS_TOKEN", "")
        if context and "gmail_token" in context:
            access_token = context["gmail_token"]
        
        if not access_token:
            return ToolResult(
                success=False,
                output="",
                error="GMAIL_ACCESS_TOKEN environment variable not set",
            )
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        try:
            if action == "send":
                return await self._send_email(parameters, headers)
            elif action == "list":
                return await self._list_emails(parameters, headers)
            elif action == "read":
                return await self._read_email(parameters, headers)
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Unknown action: {action}. Use 'send', 'list', or 'read'",
                )
        
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Gmail API error: {str(e)}",
            )
    
    async def _send_email(self, params: dict, headers: dict) -> ToolResult:
        """Send an email."""
        to = params.get("to")
        subject = params.get("subject", "")
        body = params.get("body", "")
        
        if not to:
            return ToolResult(success=False, output="", error="Recipient ('to') is required")
        
        # Create RFC 2822 message
        message = (
            f"From: me\r\n"
            f"To: {to}\r\n"
            f"Subject: {subject}\r\n"
            f"Content-Type: text/plain; charset=utf-8\r\n\r\n"
            f"{body}"
        )
        
        encoded_message = base64.urlsafe_b64encode(message.encode()).decode()
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                headers=headers,
                json={"raw": encoded_message},
            )
            
            if response.status_code == 200:
                data = response.json()
                return ToolResult(
                    success=True,
                    output=f"Email sent to {to} (ID: {data.get('id')})",
                    data=data,
                )
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Failed to send email: {response.text}",
                )
    
    async def _list_emails(self, params: dict, headers: dict) -> ToolResult:
        """List emails."""
        query = params.get("query", "")
        max_results = params.get("max_results", 10)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages",
                headers=headers,
                params={"q": query, "maxResults": max_results},
            )
            
            if response.status_code == 200:
                data = response.json()
                messages = data.get("messages", [])
                output = f"Found {len(messages)} emails:\n"
                for msg in messages[:5]:
                    output += f"- ID: {msg['id']}\n"
                return ToolResult(
                    success=True,
                    output=output,
                    data=messages,
                )
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Failed to list emails: {response.text}",
                )
    
    async def _read_email(self, params: dict, headers: dict) -> ToolResult:
        """Read a specific email."""
        message_id = params.get("message_id")
        
        if not message_id:
            return ToolResult(success=False, output="", error="message_id is required")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}",
                headers=headers,
            )
            
            if response.status_code == 200:
                data = response.json()
                # Decode body
                body = ""
                if "payload" in data:
                    body = self._extract_body(data["payload"])
                
                return ToolResult(
                    success=True,
                    output=f"Subject: {self._get_header(data, 'Subject')}\nFrom: {self._get_header(data, 'From')}\n\n{body}",
                    data=data,
                )
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Failed to read email: {response.text}",
                )
    
    def _get_header(self, message_data: dict, header_name: str) -> str:
        """Extract a header from Gmail message."""
        headers = message_data.get("payload", {}).get("headers", [])
        for h in headers:
            if h.get("name") == header_name:
                return h.get("value", "")
        return ""
    
    def _extract_body(self, payload: dict) -> str:
        """Extract email body from Gmail payload."""
        if "body" in payload and payload["body"].get("data"):
            import base64
            return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")
        
        # Multipart message
        for part in payload.get("parts", []):
            if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                import base64
                return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
        
        return "(No text body found)"
