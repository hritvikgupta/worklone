from typing import Any, Dict, List
import httpx
from urllib.parse import quote
from datetime import datetime
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class MicrosoftTeamsReadChatTool(BaseTool):
    name = "microsoft_teams_read_chat"
    description = "Read content from a Microsoft Teams chat"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="microsoft_teams_access_token",
                description="Access token for Microsoft Teams",
                env_var="MICROSOFT_TEAMS_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "microsoft-teams",
            context=context,
            context_token_keys=("microsoft_teams_access_token",),
            env_token_keys=("MICROSOFT_TEAMS_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def _extract_message_attachments(self, message: dict) -> List[Dict[str, Any]]:
        return message.get("attachments", [])

    def _format_timestamp(self, ts: str | None) -> str:
        if not ts:
            return "Unknown time"
        try:
            ts_parsed = ts.replace("Z", "+00:00")
            dt = datetime.fromisoformat(ts_parsed)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            return ts[:19] if ts and len(ts) > 19 else "Unknown time"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "chatId": {
                    "type": "string",
                    "description": "The ID of the chat to read from (e.g., \"19:abc123def456@thread.v2\" - from chat listings)",
                },
                "includeAttachments": {
                    "type": "boolean",
                    "description": "Download and include message attachments (hosted contents) into storage",
                },
            },
            "required": ["chatId"],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        chat_id = parameters.get("chatId")
        if not chat_id or not (chat_id := chat_id.strip()):
            return ToolResult(success=False, output="", error="Chat ID is required.")

        include_attachments = parameters.get("includeAttachments", False)

        headers = {
            "Authorization": f"Bearer {access_token}",
        }

        url = f"https://graph.microsoft.com/v1.0/chats/{quote(chat_id)}/messages?$top=50&$orderby=createdDateTime desc"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code not in [200]:
                    return ToolResult(success=False, output="", error=response.text)

                data = response.json()
                messages: List[Dict[str, Any]] = data.get("value", [])

                if len(messages) == 0:
                    metadata = {
                        "chatId": chat_id,
                        "messageCount": 0,
                        "messages": [],
                        "totalAttachments": 0,
                        "attachmentTypes": [],
                    }
                    content = "No messages found in this chat."
                    output_dict = {
                        "content": content,
                        "metadata": metadata,
                    }
                    return ToolResult(success=True, output=content, data=output_dict)

                chat_id_final = messages[0].get("chatId", chat_id)

                processed_messages: List[Dict[str, Any]] = []
                all_attachments: List[Dict[str, Any]] = []
                formatted_messages: List[str] = []

                for message in messages:
                    content = message.get("body", {}).get("content", "No content")
                    message_id = message.get("id")
                    sender = message.get("from", {}).get("user", {}).get("displayName", "Unknown")
                    timestamp = message.get("createdDateTime")
                    message_type = message.get("messageType", "message")

                    attachments = self._extract_message_attachments(message)
                    uploaded_files: List[Dict[str, Any]] = []

                    if include_attachments and message_id:
                        try:
                            hosted_url = f"https://graph.microsoft.com/v1.0/chats/{quote(chat_id)}/messages/{quote(message_id)}/hostedContents"
                            hresponse = await client.get(hosted_url, headers=headers)
                            if hresponse.status_code == 200:
                                hosted_contents: List[Dict[str, Any]] = hresponse.json().get("value", [])
                                attachments.extend(hosted_contents)
                        except Exception:
                            pass

                    processed_message = {
                        "id": message_id,
                        "content": content,
                        "sender": sender,
                        "timestamp": timestamp,
                        "messageType": message_type,
                        "attachments": attachments,
                        "uploadedFiles": uploaded_files,
                    }
                    processed_messages.append(processed_message)
                    all_attachments.extend(attachments)

                    formatted_ts = self._format_timestamp(timestamp)
                    formatted_msg = f"[{formatted_ts}] {sender}: {content}"
                    formatted_messages.append(formatted_msg)

                attachment_types: List[str] = []
                seen_types = set()
                for att in all_attachments:
                    ct = att.get("contentType")
                    if isinstance(ct, str) and ct and ct not in seen_types:
                        attachment_types.append(ct)
                        seen_types.add(ct)

                metadata = {
                    "chatId": chat_id_final,
                    "messageCount": len(processed_messages),
                    "totalAttachments": len(all_attachments),
                    "attachmentTypes": attachment_types,
                    "messages": processed_messages,
                }

                content = "\n\n".join(formatted_messages)
                flattened_uploads: List[Dict[str, Any]] = []
                output_dict = {
                    "content": content,
                    "metadata": metadata,
                    "attachments": flattened_uploads,
                }

                return ToolResult(success=True, output=content, data=output_dict)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")