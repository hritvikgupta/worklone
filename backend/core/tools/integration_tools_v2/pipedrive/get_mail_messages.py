from typing import Any, Dict
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class PipedriveGetMailMessagesTool(BaseTool):
    name = "pipedrive_get_mail_messages"
    description = "Retrieve mail threads from Pipedrive mailbox"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="PIPEDRIVE_ACCESS_TOKEN",
                description="Access token for the Pipedrive API",
                env_var="PIPEDRIVE_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "pipedrive",
            context=context,
            context_token_keys=("provider_token",),
            env_token_keys=("PIPEDRIVE_ACCESS_TOKEN",),
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
                    "description": "Filter by folder: inbox, drafts, sent, archive (default: inbox)",
                },
                "limit": {
                    "type": "string",
                    "description": 'Number of results to return (e.g., "25", default: 50)',
                },
                "start": {
                    "type": "string",
                    "description": "Pagination start offset (0-based index of the first item to return)",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        
        url = "https://api.pipedrive.com/v1/mailbox/mailThreads"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=parameters)
                
                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    if not data.get("success", False):
                        return ToolResult(
                            success=False,
                            output="",
                            error=data.get("error", "Failed to fetch mail threads from Pipedrive")
                        )
                    threads = data.get("data", [])
                    additional_data = data.get("additional_data", {})
                    pagination = additional_data.get("pagination", {})
                    has_more = pagination.get("more_items_in_collection", False)
                    next_start = pagination.get("next_start")
                    output_data = {
                        "messages": threads,
                        "total_items": len(threads),
                        "has_more": has_more,
                        "next_start": next_start,
                        "success": True,
                    }
                    return ToolResult(success=True, output=response.text, data=output_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")