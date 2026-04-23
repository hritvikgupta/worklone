from typing import Any, Dict, Optional, List
import httpx
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ConfluenceListSpacePermissionsTool(BaseTool):
    name = "confluence_list_space_permissions"
    description = "List permissions for a Confluence space."
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

    def _transform_permission(self, perm: Dict[str, Any]) -> Dict[str, Any]:
        subject = perm.get("subject", {})
        operation = perm.get("operation", {})
        return {
            "id": perm.get("id"),
            "principalType": subject.get("type"),
            "principalId": subject.get("id"),
            "operationKey": operation.get("key"),
            "operationTargetType": operation.get("targetType"),
            "anonymousAccess": perm.get("anonymousAccess", False),
            "unlicensedAccess": perm.get("unlicensedAccess", False),
        }

    async def _get_base_url(self, domain: str, cloud_id: Optional[str], access_token: str) -> str:
        if cloud_id:
            return f"https://api.atlassian.com/ex/confluence/{cloud_id}/api/v2"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    "https://api.atlassian.com/oauth/token/accessible-resources",
                    headers=headers,
                )
                resp.raise_for_status()
                sites: List[Dict[str, Any]] = resp.json()
                domain_url = f"https://{domain}"
                for site in sites:
                    if site.get("url") == domain_url:
                        return f"https://api.atlassian.com/ex/confluence/{site['id']}/api/v2"
                raise ValueError(f"No accessible Confluence site matching domain '{domain}' found.")
        except Exception as e:
            raise ValueError(f"Failed to fetch cloud ID for domain '{domain}': {str(e)}")

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
                    "description": "Space ID to list permissions for",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of permissions to return (default: 50, max: 250)",
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
            "required": ["domain", "spaceId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        domain: str = parameters["domain"]
        space_id: str = parameters["spaceId"]
        limit: Optional[float] = parameters.get("limit")
        limit = 50 if limit is None else min(250, max(1, int(limit)))
        cursor: Optional[str] = parameters.get("cursor")
        cloud_id: Optional[str] = parameters.get("cloudId")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        
        try:
            base_url = await self._get_base_url(domain, cloud_id, access_token)
            url = f"{base_url}/spaces/{space_id}/permissions"
            params: Dict[str, Any] = {}
            if limit:
                params["limit"] = limit
            if cursor:
                params["cursor"] = cursor
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    permissions = [
                        self._transform_permission(perm)
                        for perm in data.get("values", [])
                    ]
                    next_cursor: Optional[str] = None
                    _links = data.get("_links", {})
                    next_link = _links.get("next")
                    if isinstance(next_link, dict):
                        next_href = next_link.get("href")
                        if next_href:
                            parsed = urlparse(next_href)
                            cursor_params = parse_qs(parsed.query)
                            next_cursor = cursor_params.get("cursor", [None])[0]
                    output_data = {
                        "ts": datetime.now(timezone.utc).isoformat(),
                        "permissions": permissions,
                        "spaceId": space_id,
                        "nextCursor": next_cursor,
                    }
                    return ToolResult(success=True, output="", data=output_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")