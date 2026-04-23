from typing import Any, Dict
import httpx
import json
from datetime import datetime
from collections import defaultdict
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ConfluenceGetPageDescendantsTool(BaseTool):
    name = "confluence_get_page_descendants"
    description = "Get all descendants of a Confluence page recursively."
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
            context_token_keys=("provider_token",),
            env_token_keys=("CONFLUENCE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def _position_key(self, pos_str: str) -> tuple[int, ...]:
        if not pos_str:
            return ()
        return tuple(int(part) for part in pos_str.split('.'))

    async def _get_cloud_id(self, access_token: str, domain: str) -> str:
        url = "https://api.atlassian.com/oauth/token/accessible-resources"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                raise ValueError(f"Failed to fetch accessible resources: {resp.text}")
            resources = resp.json()
            norm_domain = domain.strip().rstrip("/")
            for resource in resources:
                resource_url = resource["url"].rstrip("/")
                if resource_url.endswith(norm_domain) or f"https://{norm_domain}" == resource_url:
                    return resource["id"]
            raise ValueError(f"No matching cloudId found for domain '{domain}'")

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
                    "description": "Page ID to get descendants for",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of descendants to return (default: 50, max: 250)",
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
        
        domain = parameters["domain"]
        page_id = parameters["pageId"]
        limit_raw = parameters.get("limit")
        cursor = parameters.get("cursor")
        cloud_id = parameters.get("cloudId")

        try:
            if limit_raw is not None:
                limit = min(int(limit_raw), 250)
            else:
                limit = 50
        except (ValueError, TypeError):
            limit = 50

        if not cloud_id:
            cloud_id = await self._get_cloud_id(access_token, domain)

        url = f"https://api.atlassian.com/ex/confluence/{cloud_id}/api/v2/pages/{page_id}/descendants"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        body = {
            "type": "page",
            "limit": limit,
            "expand": ["ancestors", "space"],
        }
        if cursor:
            body["cursor"] = cursor
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    results = data.get("results", [])
                    descendants = []
                    parent_children: dict[str, list[dict]] = defaultdict(list)
                    for page in results:
                        ancestors = page.get("ancestors", [])
                        parent_id = ancestors[0]["id"] if ancestors else page_id
                        space_obj = page.get("space", {})
                        space_id = space_obj.get("id") if space_obj else None
                        pos_str = page.get("position", "")
                        desc = {
                            "id": page["id"],
                            "title": page["title"],
                            "type": page.get("type"),
                            "status": page.get("status"),
                            "spaceId": space_id,
                            "parentId": parent_id,
                            "depth": len(ancestors),
                            "childPosition": None,
                            "temp_pos": pos_str,
                        }
                        descendants.append(desc)
                        parent_children[parent_id].append(desc)
                    
                    for children in parent_children.values():
                        children.sort(key=lambda c: self._position_key(c["temp_pos"]))
                        for i, child in enumerate(children, 1):
                            child["childPosition"] = i
                            del child["temp_pos"]
                    
                    next_cursor = data.get("pageInfo", {}).get("nextCursor", None)
                    output_data = {
                        "ts": datetime.utcnow().isoformat(),
                        "descendants": descendants,
                        "pageId": page_id,
                        "nextCursor": next_cursor,
                    }
                    return ToolResult(success=True, output=json.dumps(output_data), data=output_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")