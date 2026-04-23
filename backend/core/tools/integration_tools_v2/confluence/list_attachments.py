from typing import Any, Dict, List
import httpx
import json
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ConfluenceListAttachmentsTool(BaseTool):
    name = "confluence_list_attachments"
    description = "List all attachments on a Confluence page."
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

    async def _get_cloud_id(self, access_token: str, domain: str) -> str:
        url = "https://api.atlassian.com/oauth/token/accessible-resources"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                raise ValueError(f"Failed to fetch accessible resources: {resp.status_code} - {resp.text}")
            resources: List[Dict[str, Any]] = resp.json()
            target_url = f"https://{domain}/wiki"
            for resource in resources:
                if resource.get("url") == target_url:
                    return resource["id"]
            raise ValueError(f"No matching cloud ID found for domain '{domain}'. Available sites: {[r.get('url', 'unknown') for r in resources]}")

    def _extract_next_cursor(self, next_link: str | None) -> str | None:
        if not next_link:
            return None
        parsed = urlparse(next_link)
        query_params = parse_qs(parsed.query)
        return query_params.get("start", [None])[0]

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
                    "description": "Confluence page ID to list attachments from",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of attachments to return (default: 50, max: 250)",
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
            "required": ["domain", "pageId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        domain: str = parameters["domain"]
        page_id: str = parameters["pageId"]
        limit: int = int(parameters.get("limit", 50))
        cursor: str | None = parameters.get("cursor")
        cloud_id: str | None = parameters.get("cloudId")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        
        try:
            if not cloud_id:
                cloud_id = await self._get_cloud_id(access_token, domain)
            
            api_base = f"https://api.atlassian.com/ex/confluence/{cloud_id}/rest/api"
            url = f"{api_base}/content/{page_id}/child/attachment"
            
            start = int(cursor) if cursor else 0
            params = {
                "limit": limit,
                "start": start,
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    attachments = []
                    for att in data.get("results", []):
                        ext = att.get("extensions", {})
                        links = att.get("_links", {})
                        attachments.append({
                            "id": att["id"],
                            "title": att["title"],
                            "fileSize": ext.get("fileSize"),
                            "mediaType": ext.get("mediaType"),
                            "downloadUrl": links.get("download"),
                        })
                    next_cursor = self._extract_next_cursor(data.get("_links", {}).get("next"))
                    output_data = {
                        "ts": datetime.now(timezone.utc).isoformat(),
                        "attachments": attachments,
                        "nextCursor": next_cursor,
                    }
                    return ToolResult(success=True, output=json.dumps(output_data), data=output_data)
                else:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"API request failed: {response.status_code} - {response.text}",
                    )
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")