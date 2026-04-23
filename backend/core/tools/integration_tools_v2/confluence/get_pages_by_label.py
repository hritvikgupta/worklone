from typing import Any, Dict, Optional
import httpx
import json
from datetime import datetime
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ConfluenceGetPagesByLabelTool(BaseTool):
    name = "confluence_get_pages_by_label"
    description = "Retrieve all pages that have a specific label applied."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="CONFLUENCE_ACCESS_TOKEN",
                description="Access token",
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

    async def _get_cloud_id(self, domain: str, access_token: str) -> Optional[str]:
        url = f"https://{domain}/wiki/rest/api/instance/cloud/overview"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    return response.json().get("cloudId")
        except Exception:
            pass
        return None

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Your Confluence domain (e.g., yourcompany.atlassian.net)",
                },
                "labelId": {
                    "type": "string",
                    "description": "The ID of the label to get pages for",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of pages to return (default: 50, max: 250)",
                },
                "cursor": {
                    "type": "string",
                    "description": "Pagination cursor from previous response",
                },
                "cloudId": {
                    "type": "string",
                    "description": "Confluence Cloud ID for the instance. If not provided, it will be fetched using the domain.",
                },
            },
            "required": ["domain", "labelId"],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        domain: str = parameters["domain"]
        label_id: str = parameters["labelId"]
        limit: int = int(parameters.get("limit") or 50)
        cursor: Optional[str] = parameters.get("cursor")
        cloud_id: Optional[str] = parameters.get("cloudId")

        if cloud_id is None:
            cloud_id = await self._get_cloud_id(domain, access_token)
            if cloud_id is None:
                return ToolResult(success=False, output="", error="Could not fetch cloudId from domain.")

        base_url = f"https://api.atlassian.com/ex/confluence/{cloud_id}/wiki/rest/api"
        url = f"{base_url}/label/default/{label_id}/content"
        
        params_dict: dict = {"limit": limit}
        if cursor:
            params_dict["cursor"] = cursor
            
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params_dict, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    pages = []
                    results = data.get("results", [])
                    for result in results:
                        version = result.get("version", {})
                        page = {
                            "id": result.get("id"),
                            "title": result.get("title"),
                            "status": result.get("status"),
                            "spaceId": result.get("space", {}).get("id"),
                            "parentId": None,
                            "authorId": result.get("createdBy", {}).get("accountId"),
                            "createdAt": result.get("createdAt"),
                            "version": {
                                "number": version.get("number"),
                                "message": version.get("message"),
                                "createdAt": result.get("updatedAt"),
                            } if version.get("number") else None,
                        }
                        pages.append(page)
                    output_data = {
                        "ts": datetime.utcnow().isoformat(),
                        "labelId": label_id,
                        "pages": pages,
                        "nextCursor": data.get("_links", {}).get("next"),
                    }
                    return ToolResult(success=True, output=json.dumps(output_data), data=output_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")