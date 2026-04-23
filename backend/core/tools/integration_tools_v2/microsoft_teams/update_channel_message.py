from typing import Any, Dict
import httpx
from urllib.parse import quote
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class MicrosoftTeamsUpdateChannelMessageTool(BaseTool):
    name = "Update Microsoft Teams Channel Message"
    description = "Update an existing message in a Microsoft Teams channel"
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
                    "description": "The ID of the team (e.g., \"12345678-abcd-1234-efgh-123456789012\" - a GUID from team listings or channel info)",
                },
                "channelId": {
                    "type": "string",
                    "description": "The ID of the channel containing the message (e.g., \"19:abc123def456@thread.tacv2\" - from channel listings)",
                },
                "messageId": {
                    "type": "string",
                    "description": "The ID of the message to update (e.g., \"1234567890123\" - a numeric string from message responses)",
                },
                "content": {
                    "type": "string",
                    "description": "The new content for the message (plain text or HTML formatted)",
                },
            },
            "required": ["teamId", "channelId", "messageId", "content"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        team_id = (parameters.get("teamId") or "").strip()
        channel_id = (parameters.get("channelId") or "").strip()
        message_id = (parameters.get("messageId") or "").strip()
        content = parameters.get("content", "")
        
        if not team_id or not channel_id or not message_id or not content:
            return ToolResult(success=False, output="", error="Team ID, Channel ID, Message ID, and Content are required")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = f"https://graph.microsoft.com/v1.0/teams/{quote(team_id)}/channels/{quote(channel_id)}/messages/{quote(message_id)}"
        
        body = {
            "body": {
                "contentType": "text",
                "content": content,
            },
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    data: Dict[str, Any] = {}
                    if response.status_code != 204 and len(response.content) > 0:
                        try:
                            data = response.json()
                        except Exception:
                            pass
                    
                    metadata: Dict[str, Any] = {
                        "messageId": data.get("id") or message_id,
                        "teamId": team_id,
                        "channelId": channel_id,
                        "content": data.get("body", {}).get("content") or content,
                        "createdTime": data.get("createdDateTime", ""),
                        "url": data.get("webUrl", ""),
                    }
                    
                    output_data = {
                        "updatedContent": True,
                        "metadata": metadata,
                    }
                    
                    return ToolResult(success=True, output=str(output_data), data=output_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")