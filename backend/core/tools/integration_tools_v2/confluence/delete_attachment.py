from typing import Any, Dict
import httpx
import json
from datetime import datetime, timezone
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ConfluenceDeleteAttachmentTool(BaseTool):
    name = "confluence_delete_attachment"
    description = "Delete an attachment from a Confluence page (moves to trash)."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="CONFLUENCE_ACCESS_TOKEN",
                description="OAuth access token for Confluence",
                env_var="CONFLUENCE_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "confluence",
            context=context,
            context_token_keys=("provider_token",),
            env_token_keys=("CONFLUENCE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Your Confluence domain (e.g., yourcompany.atlassian.net)",
                },
                "attachmentId": {
                    "type": "string",
                    "description": "Confluence attachment ID to delete",
                },
                "cloudId": {
                    "type": "string",
                    "description": "Confluence Cloud ID for the instance. If not provided, it will be fetched using the domain.",
                },
            },
            "required": ["domain", "attachmentId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        domain = parameters["domain"]
        attachment_id = parameters["attachmentId"]
        cloud_id = parameters.get("cloudId")
        
        if cloud_id:
            url = f"https://api.atlassian.com/ex/confluence/{cloud_id}/wiki/rest/api/3/content/{attachment_id}"
        else:
            url = f"https://{domain}/wiki/rest/api/3/content/{attachment_id}"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)
                
                if response.status_code == 204:
                    ts = datetime.now(timezone.utc).isoformat()
                    data = {
                        "ts": ts,
                        "attachmentId": attachment_id,
                        "deleted": True,
                    }
                    return ToolResult(success=True, output=json.dumps(data), data=data)
                else:
                    return ToolResult(success=False, output="", error=f"API error ({response.status_code}): {response.text}")
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")