from typing import Any, Dict, List
import httpx
import urllib.parse
from datetime import datetime
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class MicrosoftTeamsReadChannelTool(BaseTool):
    name = "microsoft_teams_read_channel"
    description = "Read content from a Microsoft Teams channel"
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
                "teamId": {
                    "type": "string",
                    "description": "The ID of the team to read from (e.g., \"12345678-abcd-1234-efgh-123456789012\" - a GUID from team listings)",
                },
                "channelId": {
                    "type": "string",
                    "description": "The ID of the channel to read from (e.g., \"19:abc123def456@thread.tacv2\" - from channel listings)",
                },
                "includeAttachments": {
                    "type": "boolean",
                    "description": "Download and include message attachments (hosted contents) into storage",
                },
            },
            "required": ["teamId", "channelId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        
        team_id = (parameters.get("teamId") or "").strip()
        if not team_id:
            return ToolResult(success=False, output="", error="Team ID is required.")
        
        channel_id = (parameters.get("channelId") or "").strip()
        if not channel_id:
            return ToolResult(success=False, output="", error="Channel ID is required.")
        
        url = f"https://graph.microsoft.com/v1.0/teams/{urllib.parse.quote(team_id)}/channels/{urllib.parse.quote(channel_id)}/messages"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code not in [200]:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
        
        messages = data.get("value", [])
        
        if len(messages) == 0:
            return ToolResult(
                success=True,
                output="No messages found in this channel.",
                data={
                    "content": "No messages found in this channel.",
                    "metadata": {
                        "teamId": "",
                        "channelId": "",
                        "messageCount": 0,
                        "messages": [],
                        "totalAttachments": 0,
                        "attachmentTypes": [],
                    },
                    "attachments": [],
                },
            )
        
        processed_messages: List[Dict[str, Any]] = []
        for index, message in enumerate(messages):
            try:
                content = message.get("body", {}).get("content", "No content")
                message_id = message.get("id")
                
                attachments = message.get("attachments", [])
                
                sender = "Unknown"
                from_user = message.get("from", {}).get("user", {})
                if from_user.get("displayName"):
                    sender = from_user["displayName"]
                elif message.get("messageType") == "systemEventMessage":
                    sender = "System"
                
                timestamp = message.get("createdDateTime")
                message_type = message.get("messageType", "message")
                
                proc_msg: Dict[str, Any] = {
                    "id": message_id,
                    "content": content,
                    "sender": sender,
                    "timestamp": timestamp,
                    "messageType": message_type,
                    "attachments": attachments,
                    "uploadedFiles": [],
                }
                processed_messages.append(proc_msg)
            except Exception:
                proc_msg: Dict[str, Any] = {
                    "id": message.get("id", f"unknown-{index}"),
                    "content": "Error processing message",
                    "sender": "Unknown",
                    "timestamp": message.get("createdDateTime", datetime.utcnow().isoformat()),
                    "messageType": "error",
                    "attachments": [],
                    "uploadedFiles": [],
                }
                processed_messages.append(proc_msg)
        
        all_attachments: List[Dict[str, Any]] = []
        for msg in processed_messages:
            all_attachments.extend(msg.get("attachments", []))
        
        attachment_types: List[str] = []
        seen_types: set[str] = set()
        for att in all_attachments:
            ct = att.get("contentType")
            if isinstance(ct, str) and ct not in seen_types:
                attachment_types.append(ct)
                seen_types.add(ct)
        
        team_id_out = ""
        channel_id_out = ""
        if messages:
            channel_identity = messages[0].get("channelIdentity", {})
            team_id_out = channel_identity.get("teamId", "") or team_id
            channel_id_out = channel_identity.get("channelId", "") or channel_id
        
        metadata: Dict[str, Any] = {
            "teamId": team_id_out,
            "channelId": channel_id_out,
            "messageCount": len(messages),
            "totalAttachments": len(all_attachments),
            "attachmentTypes": attachment_types,
            "messages": processed_messages,
        }
        
        formatted_messages: List[str] = []
        for message in processed_messages:
            ts = message.get("timestamp")
            if ts:
                try:
                    ts_obj = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    ts_str = ts_obj.strftime("%Y-%m-%d %H:%M:%S UTC")
                except ValueError:
                    ts_str = "Unknown time"
            else:
                ts_str = "Unknown time"
            
            sender = message["sender"]
            content = message["content"]
            formatted_messages.append(f"[{ts_str}] {sender}: {content}")
        
        formatted = "\n\n".join(formatted_messages)
        
        flattened_uploads: List[Any] = []
        
        output_dict: Dict[str, Any] = {
            "content": formatted,
            "metadata": metadata,
            "attachments": flattened_uploads,
        }
        
        return ToolResult(success=True, output=formatted, data=output_dict)