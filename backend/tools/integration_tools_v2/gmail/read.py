from typing import Any, Dict, List
import httpx
import base64
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GmailReadTool(BaseTool):
    name = "Gmail Read"
    description = "Read emails from Gmail. Returns API-aligned fields only."
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
                "messageId": {
                    "type": "string",
                    "description": "Gmail message ID to read (e.g., 18f1a2b3c4d5e6f7)",
                },
                "folder": {
                    "type": "string",
                    "description": "Folder/label to read emails from (e.g., INBOX, SENT, DRAFT, TRASH, SPAM, or custom label name)",
                },
                "unreadOnly": {
                    "type": "boolean",
                    "description": "Set to true to only retrieve unread messages",
                },
                "maxResults": {
                    "type": "number",
                    "description": "Maximum number of messages to retrieve (default: 1, max: 10)",
                },
                "includeAttachments": {
                    "type": "boolean",
                    "description": "Set to true to download and include email attachments",
                },
            },
            "required": [],
        }

    def _get_headers(self, headers: List[Dict[str, Any]]) -> Dict[str, str]:
        hdict: Dict[str, str] = {}
        for h in headers:
            name = h.get("name", "").lower()
            value = h.get("value", "")
            hdict[name] = value
        return hdict

    def _extract_body(self, part: Dict[str, Any]) -> List[str]:
        texts: List[str] = []
        mime = part.get("mimeType", "").lower()
        if "text/plain" in mime:
            body_d = part.get("body", {})
            data_url = body_d.get("data", "")
            if data_url:
                try:
                    missing_padding = (4 - len(data_url) % 4) % 4
                    padded = data_url + "=" * missing_padding
                    decoded = base64.urlsafe_b64decode(padded.encode("utf-8"))
                    text = decoded.decode("utf-8", errors="ignore").strip()
                    if text:
                        texts.append(text)
                except Exception:
                    pass
        parts = part.get("parts", [])
        for p in parts:
            texts.extend(self._extract_body(p))
        return texts

    def _extract_attachments(self, part: Dict[str, Any], include: bool) -> List[Dict[str, Any]]:
        atts: List[Dict[str, Any]] = []
        if not include:
            return atts
        filename = part.get("filename", "")
        if filename:
            body_d = part.get("body", {})
            data_url = body_d.get("data", "")
            if data_url:
                try:
                    missing_padding = (4 - len(data_url) % 4) % 4
                    padded = data_url + "=" * missing_padding
                    decoded = base64.urlsafe_b64decode(padded.encode("utf-8"))
                    data_b64 = base64.b64encode(decoded).decode("utf-8")
                    atts.append({
                        "filename": filename,
                        "mimeType": part.get("mimeType", "application/octet-stream"),
                        "size_bytes": len(decoded),
                        "data_b64": data_b64,
                    })
                except Exception:
                    pass
        parts = part.get("parts", [])
        for p in parts:
            atts.extend(self._extract_attachments(p, include))
        return atts

    def _process_message(self, message_data: Dict[str, Any], include_attachments: bool) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "id": message_data.get("id"),
            "threadId": message_data.get("threadId"),
            "labelIds": message_data.get("labelIds", []),
            "from": "",
            "to": "",
            "subject": "",
            "date": "",
            "body": "",
            "hasAttachments": False,
            "attachmentCount": 0,
            "attachments": [],
        }
        payload = message_data.get("payload", {})
        headers_dict = self._get_headers(payload.get("headers", []))
        result["from"] = headers_dict.get("from", "")
        result["to"] = headers_dict.get("to", "")
        result["subject"] = headers_dict.get("subject", "")
        result["date"] = headers_dict.get("date", "")
        body_parts = self._extract_body(payload)
        body = "\n\n".join(body_parts)[:20000]
        if not body:
            body = message_data.get("snippet", "")[:20000]
        result["body"] = body
        atts = self._extract_attachments(payload, include_attachments)
        result["attachments"] = atts
        result["attachmentCount"] = len(atts)
        result["hasAttachments"] = len(atts) > 0
        return result

    def _process_summary_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "id": message_data.get("id"),
            "threadId": message_data.get("threadId"),
            "subject": "[No Subject]",
            "from": "",
            "to": "",
            "date": "",
        }
        payload = message_data.get("payload", {})
        headers_dict = self._get_headers(payload.get("headers", []))
        result["subject"] = headers_dict.get("subject", "[No Subject]")
        result["from"] = headers_dict.get("from", "")
        result["to"] = headers_dict.get("to", "")
        result["date"] = headers_dict.get("date", "")
        return result

    def _create_messages_summary(self, results: List[Dict[str, Any]]) -> str:
        if not results:
            return "No messages found."
        summary_lines = []
        for r in results:
            summary_lines.append(f"From: {r['from']} | Subject: {r['subject']} | Date: {r['date']}")
        return f"Found {len(results)} messages:\n" + "\n".join(summary_lines)

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        base_url = "https://gmail.googleapis.com/gmail/v1/users/me"
        include_att = parameters.get("includeAttachments", False)
        message_id = parameters.get("messageId")
        try:
            max_results = min(int(parameters.get("maxResults") or 1), 10)
        except ValueError:
            max_results = 1

        try:
            if message_id:
                url = f"{base_url}/messages/{message_id}?format=full"
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.get(url, headers=headers)
                    if response.status_code != 200:
                        return ToolResult(success=False, output="", error=response.text)
                    data = response.json()
                    proc = self._process_message(data, include_att)
                    return ToolResult(success=True, output=proc["body"], data=proc)
            else:
                url = f"{base_url}/messages"
                query_parts = []
                if parameters.get("unreadOnly"):
                    query_parts.append("is:unread")
                folder = (parameters.get("folder") or "").strip()
                if folder:
                    folder_upper = folder.upper()
                    if folder_upper in ["INBOX", "SENT", "DRAFT", "TRASH", "SPAM"]:
                        query_parts.append(f"in:{folder.lower()}")
                    else:
                        query_parts.append(f"label:{folder}")
                else:
                    query_parts.append("in:inbox")
                q = " ".join(query_parts)
                list_params: Dict[str, str] = {"maxResults": str(max_results)}
                if q:
                    list_params["q"] = q
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.get(url, headers=headers, params=list_params)
                    if response.status_code != 200:
                        return ToolResult(success=False, output="", error=response.text)
                    data = response.json()
                    messages_list = data.get("messages", [])
                    if not messages_list:
                        no_msg = "No messages found in the selected folder."
                        return ToolResult(success=True, output=no_msg, data={"body": no_msg, "results": []})
                    if max_results == 1:
                        msg_id = messages_list[0]["id"]
                        msg_url = f"{base_url}/messages/{msg_id}?format=full"
                        msg_resp = await client.get(msg_url, headers=headers)
                        if msg_resp.status_code != 200:
                            summaries = [{"id": msg["id"], "threadId": msg["threadId"]} for msg in messages_list]
                            err_msg = f"Found messages but couldn't retrieve details: {msg_resp.text}"
                            return ToolResult(success=True, output=err_msg, data={"body": err_msg, "results": summaries})
                        msg_data = msg_resp.json()
                        proc = self._process_message(msg_data, include_att)
                        return ToolResult(success=True, output=proc["body"], data=proc)
                    else:
                        summary_results: List[Dict[str, Any]] = []
                        all_atts: List[Dict[str, Any]] = []
                        for msg in messages_list[:max_results]:
                            msg_id = msg["id"]
                            msg_url = f"{base_url}/messages/{msg_id}?format=full"
                            msg_resp = await client.get(msg_url, headers=headers)
                            if msg_resp.status_code != 200:
                                summary_results.append({
                                    "id": msg_id,
                                    "threadId": msg["threadId"],
                                    "subject": "Failed to fetch",
                                    "from": "",
                                    "to": "",
                                    "date": "",
                                })
                                continue
                            msg_data = msg_resp.json()
                            summary = self._process_summary_message(msg_data)
                            summary_results.append(summary)
                            if include_att:
                                proc = self._process_message(msg_data, True)
                                all_atts.extend(proc["attachments"])
                        summary_content = self._create_messages_summary(summary_results)
                        data_out = {
                            "body": summary_content,
                            "results": summary_results,
                            "attachments": all_atts,
                        }
                        return ToolResult(success=True, output=summary_content, data=data_out)
    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")