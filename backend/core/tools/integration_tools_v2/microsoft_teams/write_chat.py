from typing import Any, Dict
import httpx
import json
import re
from urllib.parse import quote
from datetime import datetime, timezone
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class MicrosoftTeamsWriteChatTool(BaseTool):
    name = "microsoft_teams_write_chat"
    description = "Write or update content in a Microsoft Teams chat"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="MICROSOFT_TEAMS_ACCESS_TOKEN",
                description="Access token for the Microsoft Teams API",
                env_var="MICROSOFT_TEAMS_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "microsoft-teams",
            context=context,
            context_token_keys=("access_token",),
            env_token_keys=("MICROSOFT_TEAMS_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "chatId": {
                    "type": "string",
                    "description": "The ID of the chat to write to (e.g., \"19:abc123def456@thread.v2\" - from chat listings)",
                },
                "content": {
                    "type": "string",
                    "description": "The content to write to the message (plain text or HTML formatted, supports @mentions)",
                },
                "files": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "File name",
                            },
                            "mimeType": {
                                "type": "string",
                                "description": "MIME type of the file",
                            },
                            "content": {
                                "type": "string",
                                "description": "Base64 encoded content of the file",
                            },
                        },
                        "required": ["name", "content"],
                        "additionalProperties": False,
                    },
                    "description": "Files to attach to the message",
                },
            },
            "required": ["chatId", "content"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        chat_id = parameters.get("chatId", "").strip()
        if not chat_id:
            return ToolResult(success=False, output="", error="Chat ID is required.")

        content = parameters.get("content", "")
        if not content:
            return ToolResult(success=False, output="", error="Content is required.")

        files = parameters.get("files", [])

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        url = f"https://graph.microsoft.com/v1.0/chats/{quote(chat_id)}/messages"

        async with httpx.AsyncClient(timeout=30.0) as client:
            mention_entities: list[dict] = []
            message_content = content
            content_type = "text"
            attachment_count = 0
            attachments: list[dict] = []

            # Handle mentions
            mention_pattern = re.compile(r"<at>([^<]+)</at>", re.IGNORECASE)
            if mention_pattern.search(content):
                try:
                    members_url = f"https://graph.microsoft.com/v1.0/chats/{quote(chat_id)}/members"
                    members_resp = await client.get(members_url, headers=headers)
                    if members_resp.status_code == 200:
                        members_data = members_resp.json()
                        members = members_data.get("value", [])
                        name_to_member: dict[str, dict] = {}
                        for member in members:
                            user_id = member.get("userId")
                            if user_id:
                                name_lower = member.get("displayName", "").lower()
                                name_to_member[name_lower] = member

                        matches = list(mention_pattern.finditer(content))
                        updated_parts: list[str] = []
                        last_end = 0
                        mention_index = 0
                        for match in matches:
                            start, end = match.span()
                            mention_text = match.group(1).strip()
                            updated_parts.append(content[last_end:start])
                            member = name_to_member.get(mention_text.lower())
                            if member:
                                att_id = str(mention_index)
                                updated_parts.append(f'<at id="{att_id}">{mention_text}</at>')
                                mention_entities.append(
                                    {
                                        "id": mention_index,
                                        "mentionText": f"@{mention_text}",
                                        "mentioned": {
                                            "user": {
                                                "id": member["userId"],
                                                "displayName": member["displayName"],
                                                "userIdentityType": "aadUser",
                                            }
                                        },
                                    }
                                )
                                mention_index += 1
                            else:
                                updated_parts.append(match.group(0))
                            last_end = end
                        updated_parts.append(content[last_end:])
                        message_content = "".join(updated_parts)
                except Exception:
                    pass  # continue without mentions

            # Handle files
            if files:
                for i, file_info in enumerate(files):
                    if isinstance(file_info, dict) and file_info.get("name") and file_info.get("content"):
                        att_id = f"attachment_{i}"
                        att = {
                            "id": att_id,
                            "name": file_info["name"],
                            "contentType": file_info.get("mimeType", "application/octet-stream"),
                            "contentBytes": file_info["content"],
                        }
                        attachments.append(att)
                        attachment_count += 1

            if attachments:
                content_type = "html"
                attachment_tags = " ".join([f'<attachment id="{att["id"]}"></attachment>' for att in attachments])
                message_content += f"<br/>{attachment_tags}"

            if mention_entities:
                content_type = "html"

            body = {
                "body": {
                    "contentType": content_type,
                    "content": message_content,
                }
            }
            if attachments:
                body["attachments"] = attachments
            if mention_entities:
                body["mentions"] = mention_entities

            try:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    metadata = {
                        "messageId": data.get("id", ""),
                        "chatId": data.get("chatId", chat_id),
                        "content": data.get("body", {}).get("content", content),
                        "createdTime": data.get("createdDateTime", datetime.now(timezone.utc).isoformat()),
                        "url": data.get("webUrl", ""),
                    }
                    if attachment_count > 0:
                        metadata["attachmentCount"] = attachment_count
                    files_output = files
                    output_dict = {
                        "updatedContent": True,
                        "metadata": metadata,
                        "files": files_output,
                    }
                    return ToolResult(
                        success=True, output=json.dumps(output_dict), data=output_dict
                    )
                else:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("error", {}).get("message", response.text)
                    except Exception:
                        error_msg = response.text
                    return ToolResult(success=False, output="", error=error_msg)

            except Exception as e:
                return ToolResult(success=False, output="", error=f"API error: {str(e)}")