from typing import Any, Dict, List
import httpx
import base64
import json
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class DiscordSendMessageTool(BaseTool):
    name = "discord_send_message"
    description = "Send a message to a Discord channel"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="botToken",
                description="The bot token for authentication",
                env_var="DISCORD_BOT_TOKEN",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "discord",
            context=context,
            context_token_keys=("botToken",),
            env_token_keys=("DISCORD_BOT_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "channelId": {
                    "type": "string",
                    "description": "The Discord channel ID to send the message to, e.g., 123456789012345678",
                },
                "content": {
                    "type": "string",
                    "description": "The text content of the message",
                },
                "serverId": {
                    "type": "string",
                    "description": "The Discord server ID (guild ID), e.g., 123456789012345678",
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
                            "data": {
                                "type": "string",
                                "description": "Base64 encoded file content",
                            },
                        },
                        "required": ["name", "data"],
                    },
                    "description": "Files to attach to the message",
                },
            },
            "required": ["channelId", "serverId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        channel_id = parameters.get("channelId")
        if not channel_id or not channel_id.isdigit():
            return ToolResult(success=False, output="", error="Invalid channel ID format.")
        
        content = parameters.get("content", "")
        files_param: List[Dict[str, Any]] = parameters.get("files", [])
        
        url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
        headers_base = {
            "Authorization": f"Bot {access_token}",
        }
        
        valid_files = []
        for i, file_info in enumerate(files_param):
            if isinstance(file_info, dict) and "data" in file_info:
                try:
                    name = file_info.get("name", f"file_{i}")
                    mime_type = file_info.get("mimeType", "application/octet-stream")
                    data_b64 = file_info["data"]
                    data = base64.b64decode(data_b64)
                    valid_files.append({"name": name, "mime_type": mime_type, "data": data})
                except Exception:
                    pass
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if not valid_files:
                    headers = {**headers_base, "Content-Type": "application/json"}
                    body = {"content": content}
                    response = await client.post(url, headers=headers, json=body)
                else:
                    multipart_files = [
                        (
                            "payload_json",
                            (None, json.dumps({"content": content}), "application/json"),
                        )
                    ]
                    for i, f in enumerate(valid_files):
                        multipart_files.append(
                            (
                                f"files[{i}]",
                                (f["name"], f["data"], f["mime_type"]),
                            )
                        )
                    headers = headers_base
                    response = await client.post(url, headers=headers, files=multipart_files)
                
                if response.status_code in [200, 201]:
                    return ToolResult(
                        success=True, output=response.text, data=response.json()
                    )
                else:
                    return ToolResult(
                        success=False, output="", error=response.text
                    )
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")