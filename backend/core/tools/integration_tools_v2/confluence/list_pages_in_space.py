from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ConfluenceListPagesInSpaceTool(BaseTool):
    name = "confluence_list_pages_in_space"
    description = "List all pages within a specific Confluence space. Supports pagination and filtering by status."
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
            context_token_keys=("accessToken",),
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
                "spaceId": {
                    "type": "string",
                    "description": "The ID of the Confluence space to list pages from",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of pages to return (default: 50, max: 250)",
                },
                "status": {
                    "type": "string",
                    "description": "Filter pages by status: current, archived, trashed, or draft",
                },
                "bodyFormat": {
                    "type": "string",
                    "description": "Format for page body content: storage, atlas_doc_format, or view. If not specified, body is not included.",
                },
                "cursor": {
                    "type": "string",
                    "description": "Pagination cursor from previous response to get the next page of results",
                },
                "cloudId": {
                    "type": "string",
                    "description": "Confluence Cloud ID for the instance. If not provided, it will be fetched using the domain.",
                },
            },
            "required": ["domain", "spaceId"],
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
        space_id = parameters["spaceId"].strip()
        limit = min(int(parameters.get("limit", 50)), 250)
        status = parameters.get("status")
        body_format = parameters.get("bodyFormat")
        cursor = parameters.get("cursor")
        cloud_id = parameters.get("cloudId")
        
        if cloud_id:
            url = f"https://api.atlassian.com/ex/confluence/{cloud_id.rstrip('/')}/wiki/api/v2/spaces/{space_id}/pages"
        else:
            url = f"https://{domain.rstrip('/')}/wiki/api/v2/spaces/{space_id}/pages"
        
        query_params: Dict[str, Any] = {
            "limit": limit,
        }
        if status:
            query_params["statuses"] = [status]
        if body_format:
            query_params["body.format"] = body_format
        if cursor:
            query_params["cursor"] = cursor
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")