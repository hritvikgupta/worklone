from typing import Any, Dict
import httpx
from datetime import datetime
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ConfluenceDeletePageTool(BaseTool):
    name = "confluence_delete_page"
    description = "Delete a Confluence page. By default moves to trash; use purge=true to permanently delete."
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
                "pageId": {
                    "type": "string",
                    "description": "Confluence page ID to delete",
                },
                "purge": {
                    "type": "boolean",
                    "description": "If true, permanently deletes the page instead of moving to trash (default: false)",
                },
                "cloudId": {
                    "type": "string",
                    "description": "Confluence Cloud ID for the instance. If not provided, it will be fetched using the domain.",
                },
            },
            "required": ["domain", "pageId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        
        domain = parameters["domain"]
        page_id = parameters["pageId"]
        purge = parameters.get("purge", False)
        cloud_id = parameters.get("cloudId")
        
        base_url = f"https://{domain}.atlassian.net"
        content_url = f"{base_url}/wiki/rest/api/content/{page_id}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if purge:
                    # First move to trash
                    trash_resp = await client.delete(content_url, headers=headers)
                    if trash_resp.status_code not in [200, 204]:
                        return ToolResult(
                            success=False,
                            output="",
                            error=f"Failed to move page to trash: {trash_resp.status_code} - {trash_resp.text}"
                        )
                    
                    # Then permanently delete from trash
                    purge_url = f"{content_url}?status=trash"
                    purge_resp = await client.delete(purge_url, headers=headers)
                    if purge_resp.status_code not in [200, 204]:
                        return ToolResult(
                            success=False,
                            output="",
                            error=f"Failed to permanently delete page: {purge_resp.status_code} - {purge_resp.text}"
                        )
                else:
                    resp = await client.delete(content_url, headers=headers)
                    if resp.status_code not in [200, 204]:
                        return ToolResult(
                            success=False,
                            output="",
                            error=f"{resp.status_code} - {resp.text}"
                        )
                
                output_data = {
                    "ts": datetime.utcnow().isoformat(),
                    "pageId": page_id,
                    "deleted": True,
                }
                return ToolResult(
                    success=True,
                    output=str(output_data),
                    data=output_data
                )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")