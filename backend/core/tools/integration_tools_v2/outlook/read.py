from typing import Any, Dict, List
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class OutlookReadTool(BaseTool):
    name = "outlook_read"
    description = "Read emails from Outlook"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="OUTLOOK_ACCESS_TOKEN",
                description="Access token",
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
                "folder": {
                    "type": "string",
                    "description": 'Folder ID to read emails from (e.g., "Inbox", "Drafts", or a folder ID)'
                },
                "maxResults": {
                    "type": "number",
                    "description": "Maximum number of emails to retrieve (default: 1, max: 10)"
                },
                "includeAttachments": {
                    "type": "boolean",
                    "description": "Whether to download and include email attachments"
                }
            },
            "required": []
        }

    async def _download_attachments(self, message_id: str, access_token: str) -> List[Dict[str, Any]]:
        attachments: List[Dict[str, Any]] = []
        att_url = f"https://graph.microsoft.com/v1.0/me/messages/{message_id}/attachments"
        att_headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                att_resp = await client.get(att_url, headers=att_headers)
                if att_resp.status_code != 200:
                    return attachments
                att_data = att_resp.json()
                att_list = att_data.get("value", [])
                for att in att_list:
                    if att.get("@odata.type") == "#microsoft.graph.fileAttachment":
                        content_bytes = att.get("contentBytes")
                        if content_bytes:
                            try:
                                decoded = base64.b64decode(content_bytes)
                                norm_data = base64.b64encode(decoded).decode("ascii")
                                attachments.append({
                                    "name": att.get("name"),
                                    "data": norm_data,
                                    "contentType": att.get("contentType"),
                                    "size": att.get("size"),
                                })
                            except Exception:
                                pass
        except Exception:
            pass
        return attachments

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        
        folder = parameters.get("folder")
        max_results_raw = parameters.get("maxResults")
        max_results = 1
        if max_results_raw is not None:
            try:
                mr = abs(float(max_results_raw))
                max_results = max(1, min(int(mr), 10))
            except (ValueError, TypeError):
                pass
        include_attachments = parameters.get("includeAttachments", False)
        
        if folder:
            url = f"https://graph.microsoft.com/v1.0/me/mailFolders/{folder}/messages?$top={max_results}&$orderby=createdDateTime desc"
        else:
            url = f"https://graph.microsoft.com/v1.0/me/messages?$top={max_results}&$orderby=createdDateTime desc"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code != 200:
                    return ToolResult(success=False, output="", error=response.text)
                    
                data = response.json()
                messages = data.get("value", [])
                
                cleaned_messages: List[Dict[str, Any]] = []
                all_attachments: List[Dict[str, Any]] = []
                
                for message in messages:
                    atts = []
                    if include_attachments and message.get("hasAttachments") and access_token:
                        atts = await self._download_attachments(message["id"], access_token)
                    
                    cleaned = {
                        "id": message.get("id"),
                        "subject": message.get("subject"),
                        "bodyPreview": message.get("bodyPreview"),
                        "body": {
                            "contentType": message.get("body", {}).get("contentType"),
                            "content": message.get("body", {}).get("content"),
                        },
                        "sender": {
                            "name": message.get("sender", {}).get("emailAddress", {}).get("name"),
                            "address": message.get("sender", {}).get("emailAddress", {}).get("address"),
                        },
                        "from": {
                            "name": message.get("from", {}).get("emailAddress", {}).get("name"),
                            "address": message.get("from", {}).get("emailAddress", {}).get("address"),
                        },
                        "toRecipients": [
                            {
                                "name": r.get("emailAddress", {}).get("name"),
                                "address": r.get("emailAddress", {}).get("address"),
                            }
                            for r in message.get("toRecipients", [])
                        ],
                        "ccRecipients": [
                            {
                                "name": r.get("emailAddress", {}).get("name"),
                                "address": r.get("emailAddress", {}).get("address"),
                            }
                            for r in message.get("ccRecipients", [])
                        ],
                        "receivedDateTime": message.get("receivedDateTime"),
                        "sentDateTime": message.get("sentDateTime"),
                        "hasAttachments": message.get("hasAttachments"),
                        "attachments": atts,
                        "isRead": message.get("isRead"),
                        "importance": message.get("importance"),
                    }
                    cleaned_messages.append(cleaned)
                    if atts:
                        all_attachments.extend(atts)
                
                if not cleaned_messages:
                    transformed = {
                        "message": "No mail found.",
                        "results": [],
                        "attachments": [],
                    }
                else:
                    transformed = {
                        "message": f"Successfully read {len(cleaned_messages)} email(s).",
                        "results": cleaned_messages,
                        "attachments": all_attachments,
                    }
                    
                return ToolResult(success=True, output=transformed["message"], data=transformed)
                
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")