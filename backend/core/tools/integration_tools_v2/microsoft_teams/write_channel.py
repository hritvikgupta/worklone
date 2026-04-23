from typing import Any, Dict, List, Optional
import httpx
import base64
import re
import json
import urllib.parse
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class MicrosoftTeamsWriteChannelTool(BaseTool):
    name = "microsoft_teams_write_channel"
    description = "Write or send a message to a Microsoft Teams channel"
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
            context_token_keys=("accessToken",),
            env_token_keys=("MICROSOFT_TEAMS_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "teamId": {
                    "type": "string",
                    "description": "The ID of the team to write to (e.g., \"12345678-abcd-1234-efgh-123456789012\" - a GUID from team listings)",
                },
                "channelId": {
                    "type": "string",
                    "description": "The ID of the channel to write to (e.g., \"19:abc123def456@thread.tacv2\" - from channel listings)",
                },
                "content": {
                    "type": "string",
                    "description": "The content to write to the channel (plain text or HTML formatted, supports @mentions)",
                },
                "files": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "data": {"type": "string"},
                            "type": {"type": "string"},
                        },
                    },
                    "description": "Files to attach to the message",
                },
            },
            "required": ["teamId", "channelId", "content"],
        }

    async def _find_team_member(self, team_id: str, name: str, access_token: str) -> Optional[Dict[str, str]]:
        members_url = f"https://graph.microsoft.com/v1.0/teams/{urllib.parse.quote(team_id)}/members?$top=999&$select=displayName,userId,email"
        headers = {"Authorization": f"Bearer {access_token}"}
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(members_url, headers=headers)
                if resp.status_code != 200:
                    return None
                members_data = resp.json()
                members = members_data.get("value", [])
                name_lower = name.lower()
                for member in members:
                    display_name = member.get("displayName", "").lower()
                    email = member.get("email", "").lower()
                    if name_lower in display_name or name_lower in email:
                        return {
                            "id": member["userId"],
                            "displayName": member["displayName"],
                        }
                return None
        except Exception:
            return None

    async def _resolve_mentions(self, team_id: str, content: str, access_token: str) -> Dict[str, Any]:
        mention_matches = list(re.finditer(r"<at>([^<]+)</at>", content, re.IGNORECASE))
        if not mention_matches:
            return {"has_mentions": False, "updated_content": content, "mentions": []}
        mentions = []
        updated_content_parts = []
        last_end = 0
        for i, match in enumerate(mention_matches):
            start, end = match.span()
            text = match.group(1).strip()
            updated_content_parts.append(content[last_end:start])
            user = await self._find_team_member(team_id, text, access_token)
            if user:
                user_id = user["id"]
                display_name = user["displayName"]
                replacement = f'<at id="{user_id}">{display_name}</at>'
                updated_content_parts.append(replacement)
                mention = {
                    "id": i,
                    "mentionText": f"@{display_name}",
                    "mentioned": {
                        "user": {
                            "id": user_id,
                            "displayName": display_name,
                        }
                    },
                }
                mentions.append(mention)
            else:
                updated_content_parts.append(match.group(0))
            last_end = end
        updated_content_parts.append(content[last_end:])
        updated_content = "".join(updated_content_parts)
        return {
            "has_mentions": bool(mentions),
            "updated_content": updated_content,
            "mentions": mentions,
        }

    def _handle_files(self, files: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        attachments: List[Dict[str, Any]] = []
        files_output: List[Dict[str, Any]] = []
        total_bytes = 0
        for i, f in enumerate(files):
            name = f.get("name")
            if not name:
                continue
            data_b64 = f.get("data")
            if not data_b64:
                continue
            try:
                content_bytes = base64.b64decode(data_b64)
                size = len(content_bytes)
                if size > 10000 or total_bytes + size > 20000:
                    raise ValueError(f"File {name} too large ({size} bytes) or total exceeds limit")
                total_bytes += size
                att: Dict[str, Any] = {
                    "id": str(i),
                    "contentType": "fileAttachment",
                    "name": name,
                    "contentBytes": data_b64,
                }
                attachments.append(att)
                files_output.append({
                    "name": name,
                    "size": size,
                })
            except Exception as e:
                raise ValueError(f"Invalid file {name}: {str(e)}")
        return attachments, files_output

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        team_id = parameters.get("teamId", "").strip()
        if not team_id:
            return ToolResult(success=False, output="", error="Team ID is required")
        channel_id = parameters.get("channelId", "").strip()
        if not channel_id:
            return ToolResult(success=False, output="", error="Channel ID is required")
        content = parameters.get("content", "").strip()
        if not content:
            return ToolResult(success=False, output="", error="Message content is required")
        files = parameters.get("files", [])
        attachments: List[Dict[str, Any]] = []
        mention_entities: List[Dict[str, Any]] = []
        files_output: List[Dict[str, Any]] = []
        message_content = content
        content_type = "text"
        has_mentions = bool(re.search(r"<at[^>]*>.*?</at>", content, re.IGNORECASE))
        if has_mentions:
            try:
                mention_result = await self._resolve_mentions(team_id, content, access_token)
                message_content = mention_result["updated_content"]
                mention_entities = mention_result["mentions"]
                if mention_entities:
                    content_type = "html"
            except Exception:
                pass
        if files:
            try:
                attachments, files_output = self._handle_files(files)
                if attachments:
                    content_type = "html"
                    att_tags = " ".join([f'<attachment id="{att["id"]}"></attachment>' for att in attachments])
                    message_content += f"<br/>{att_tags}"
            except Exception as e:
                return ToolResult(success=False, output="", error=str(e))
        body = {
            "body": {
                "contentType": content_type,
                "content": message_content,
            }
        }
        if mention_entities:
            body["mentions"] = mention_entities
        if attachments:
            body["attachments"] = attachments
        url = f"https://graph.microsoft.com/v1.0/teams/{urllib.parse.quote(team_id)}/channels/{urllib.parse.quote(channel_id)}/messages"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                if response.status_code in [200, 201, 202]:
                    data = response.json()
                    metadata = {
                        "messageId": data.get("id", ""),
                        "teamId": data.get("channelIdentity", {}).get("teamId", team_id),
                        "channelId": data.get("channelIdentity", {}).get("channelId", channel_id),
                        "content": data.get("body", {}).get("content", content),
                        "createdTime": data.get("createdDateTime", ""),
                        "url": data.get("webUrl", ""),
                    }
                    output_data = {
                        "updatedContent": True,
                        "metadata": metadata,
                    }
                    if files_output:
                        output_data["files"] = files_output
                        metadata["attachmentCount"] = len(files_output)
                    return ToolResult(success=True, output=response.text, data=output_data)
                else:
                    error_text = response.text
                    try:
                        err_data = response.json()
                        error_msg = err_data.get("error", {}).get("message", error_text)
                    except Exception:
                        error_msg = error_text
                    return ToolResult(success=False, output="", error=error_msg)
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")