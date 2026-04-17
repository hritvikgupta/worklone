from typing import Any, Dict
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GmailGetDraftTool(BaseTool):
    name = "gmail_get_draft"
    description = "Get a specific draft from Gmail by its ID"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GMAIL_ACCESS_TOKEN",
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

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "draftId": {
                    "type": "string",
                    "description": "ID of the draft to retrieve",
                }
            },
            "required": ["draftId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        draft_id = parameters["draftId"]
        url = f"https://gmail.googleapis.com/gmail/v1/drafts/{draft_id}?format=full"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    message = data.get("message", {})
                    payload = message.get("payload", {})
                    headers_list = payload.get("headers", [])
                    
                    def get_header(name: str) -> str | None:
                        lower_name = name.lower()
                        for h in headers_list:
                            if h.get("name", "").lower() == lower_name:
                                return h.get("value")
                        return None
                    
                    to_email = get_header("To")
                    from_email = get_header("From")
                    subject = get_header("Subject")
                    
                    body = None
                    body_data = payload.get("body", {}).get("data")
                    if body_data:
                        padded = body_data + "=" * ((4 - len(body_data) % 4) % 4)
                        body_bytes = base64.urlsafe_b64decode(padded)
                        body = body_bytes.decode("utf-8")
                    else:
                        parts = payload.get("parts", [])
                        for part in parts:
                            if part.get("mimeType") == "text/plain":
                                part_body_data = part.get("body", {}).get("data")
                                if part_body_data:
                                    padded = part_body_data + "=" * ((4 - len(part_body_data) % 4) % 4)
                                    body_bytes = base64.urlsafe_b64decode(padded)
                                    body = body_bytes.decode("utf-8")
                                    break
                    
                    transformed = {
                        "id": data.get("id"),
                        "messageId": message.get("id"),
                        "threadId": message.get("threadId"),
                        "to": to_email,
                        "from": from_email,
                        "subject": subject,
                        "body": body,
                        "labelIds": message.get("labelIds"),
                    }
                    return ToolResult(success=True, output=str(transformed), data=transformed)
                else:
                    error_msg = response.text
                    try:
                        err_data = response.json()
                        if isinstance(err_data, dict) and "error" in err_data:
                            error_msg = err_data["error"].get("message", error_msg)
                    except ValueError:
                        pass
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")