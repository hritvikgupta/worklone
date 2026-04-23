from typing import Any, Dict, Optional
import httpx
import json
from datetime import datetime, timezone
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ConfluenceListBlogPostsTool(BaseTool):
    name = "confluence_list_blogposts"
    description = "List all blog posts across all accessible Confluence spaces."
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
            context_token_keys=("confluence_token",),
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
                "limit": {
                    "type": "number",
                    "description": "Maximum number of blog posts to return (default: 25, max: 250)",
                },
                "status": {
                    "type": "string",
                    "description": "Filter by status: current, archived, trashed, or draft",
                },
                "sort": {
                    "type": "string",
                    "description": "Sort order: created-date, -created-date, modified-date, -modified-date, title, -title",
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
            "required": ["domain"],
        }

    async def _get_cloud_id(self, access_token: str, domain: str, cloud_id: Optional[str], client: httpx.AsyncClient) -> str:
        if cloud_id:
            return cloud_id
        url = "https://api.atlassian.com/oauth/token/accessible-resources"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        sites = response.json()
        site_url = f"https://{domain.rstrip('/')}/wiki"
        for site in sites:
            if site.get("url") == site_url:
                return site["id"]
        raise ValueError(f"No Confluence site found for domain {domain}")

    def _map_sort(self, sort: str) -> str:
        mapping: Dict[str, str] = {
            "created-date": "created",
            "-created-date": "-created",
            "modified-date": "modified",
            "-modified-date": "-modified",
        }
        return mapping.get(sort, sort)

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        domain: str = parameters["domain"]
        limit: int = min(250, max(1, parameters.get("limit", 25)))
        status: Optional[str] = parameters.get("status")
        sort: Optional[str] = parameters.get("sort")
        cursor: Optional[str] = parameters.get("cursor")
        cloud_id: Optional[str] = parameters.get("cloudId")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                cloud_id_resolved = await self._get_cloud_id(access_token, domain, cloud_id, client)

                start = int(cursor) if cursor else 0

                cql = "type = blogpost"
                if status:
                    cql += f" AND status = {status}"

                query_params: Dict[str, str] = {
                    "cql": cql,
                    "limit": str(limit),
                    "start": str(start),
                    "expand": "space,history.latest.createdBy,history.latest.createdDate,version,_links",
                }
                if sort:
                    query_params["sort"] = self._map_sort(sort)

                url = f"https://api.atlassian.com/ex/confluence/{cloud_id_resolved}/wiki/rest/api/search"

                response = await client.get(url, params=query_params, headers=headers)

                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    blog_posts = []
                    for result in results:
                        space = result.get("space", {})
                        space_id = space.get("id") if space else None
                        history_latest = result.get("history", {}).get("latest", {})
                        author_id = history_latest.get("createdBy", {}).get("accountId")
                        created_at = history_latest.get("createdDate")
                        version = result.get("version")
                        version_info = None
                        if version:
                            version_info = {
                                "number": version["number"],
                                "message": version.get("message"),
                                "createdAt": version.get("when"),
                            }
                        bp = {
                            "id": result["id"],
                            "title": result["title"],
                            "status": result.get("status"),
                            "spaceId": space_id,
                            "authorId": author_id,
                            "createdAt": created_at,
                            "version": version_info,
                            "webUrl": result.get("_links", {}).get("webui"),
                        }
                        blog_posts.append(bp)

                    next_cursor = None
                    next_start = data.get("start", 0) + len(results)
                    if len(results) == limit:
                        next_cursor = str(next_start)

                    output_dict = {
                        "ts": datetime.now(timezone.utc).isoformat(),
                        "blogPosts": blog_posts,
                        "nextCursor": next_cursor,
                    }
                    output_str = json.dumps(output_dict)
                    return ToolResult(success=True, output=output_str, data=output_dict)
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")