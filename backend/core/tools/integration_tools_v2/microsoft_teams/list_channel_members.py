from typing import Any, Dict, List
import httpx
import urllib.parse
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class MicrosoftTeamsListChannelMembersTool(BaseTool):
    name = "microsoft_teams_list_channel_members"
    description = "List all members of a Microsoft Teams channel"
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
                    "description": "The ID of the team (e.g., \"12345678-abcd-1234-efgh-123456789012\" - a GUID from team listings)",
                },
                "channelId": {
                    "type": "string",
                    "description": "The ID of the channel (e.g., \"19:abc123def456@thread.tacv2\" - from channel listings)",
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
        
        team_id = parameters.get("teamId", "").strip()
        channel_id = parameters.get("channelId", "").strip()
        if not team_id or not channel_id:
            return ToolResult(success=False, output="", error="Team ID and Channel ID are required")
        
        url = f"https://graph.microsoft.com/v1.0/teams/{urllib.parse.quote(team_id)}/channels/{urllib.parse.quote(channel_id)}/members"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    members = [
                        {
                            "id": member.get("id", ""),
                            "displayName": member.get("displayName", ""),
                            "email": member.get("email") or member.get("userId", ""),
                            "userId": member.get("userId", ""),
                            "roles": member.get("roles", []),
                        }
                        for member in data.get("value", [])
                    ]
                    transformed = {
                        "members": members,
                        "memberCount": len(members),
                        "metadata": {
                            "teamId": team_id,
                            "channelId": channel_id,
                        },
                    }
                    return ToolResult(success=True, output=response.text, data=transformed)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")