from typing import Any, Dict, Optional
import httpx
import json
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ConfluenceListBlogPostsInSpaceTool(BaseTool):
    name = "confluence_list_blogposts_in_space"
    description = "List all blog posts within a specific Confluence space."
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
                    "description": "The ID of the Confluence space to list blog posts from",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of blog posts to return (default: 25, max: 250)",
                },
                "status": {
                    "type": "string",
                    "description": "Filter by status: current, archived, trashed, or draft",
                },
                "bodyFormat": {
                    "type": "string",
                    "description": "Format for blog post body: storage, atlas_doc_format, or view",
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
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        
        domain: str = parameters["domain"]
        space_id: str = parameters["spaceId"].strip()
        limit: Optional[int] = parameters.get("limit")
        if limit is not None:
            limit = int(limit)
        else:
            limit = 25
        status: Optional[str] = parameters.get("status")
        body_format: Optional[str] = parameters.get("bodyFormat")
        cursor: Optional[str] = parameters.get("cursor")
        cloud_id: Optional[str] = parameters.get("cloudId")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Fetch cloudId if not provided
                if not cloud_id:
                    instance_url = f"https://{domain}.atlassian.net/wiki/rest/api/instance"
                    instance_response = await client.get(instance_url, headers=headers)
                    if instance_response.status_code != 200:
                        return ToolResult(
                            success=False,
                            output="",
                            error=f"Failed to fetch cloudId: {instance_response.text}",
                        )
                    instance_data = instance_response.json()
                    cloud_id = instance_data.get("cloudId")
                    if not cloud_id:
                        return ToolResult(
                            success=False,
                            output="",
                            error="CloudId not found in instance response.",
                        )
                
                # Build API URL
                base_url = f"https://api.atlassian.com/ex/confluence/{cloud_id}/wiki/api/v2"
                url = f"{base_url}/spaces/{space_id}/blogposts"
                
                # Build query params
                query_params: Dict[str, Any] = {}
                if limit is not None:
                    query_params["limit"] = limit
                if status:
                    query_params["status"] = status
                if body_format:
                    query_params["body.format"] = body_format
                if cursor:
                    query_params["cursor"] = cursor
                
                # Expands for required fields
                expand_list = ["version", "creator"]
                if body_format:
                    expand_list.append(f"body.{body_format}")
                query_params["expand"] = ",".join(expand_list)
                
                response = await client.get(url, headers=headers, params=query_params)
                
                if response.status_code in [200]:
                    data = response.json()
                    results = data.get("results", [])
                    
                    blog_posts = []
                    for item in results:
                        body_raw = item.get("body")
                        body_transformed = None
                        if body_raw:
                            representation = body_raw.get("representation")
                            if representation == "storage":
                                body_transformed = {"storage": {"value": body_raw.get("value", "")}}
                            elif representation == "atlas_doc_format":
                                body_transformed = {"atlas_doc_format": {"value": body_raw.get("value", "")}}
                            elif representation == "view":
                                body_transformed = {"view": {"value": body_raw.get("value", "")}}
                            else:
                                body_transformed = body_raw
                        
                        bp = {
                            "id": item.get("id"),
                            "title": item.get("title"),
                            "status": item.get("status"),
                            "spaceId": item.get("spaceId"),
                            "authorId": item.get("creator", {}).get("accountId"),
                            "createdAt": item.get("createdAt"),
                            "version": item.get("version"),
                            "body": body_transformed,
                            "webUrl": item.get("_links", {}).get("webui"),
                        }
                        blog_posts.append(bp)
                    
                    next_cursor = None
                    links = data.get("_links", {})
                    if "next" in links:
                        next_url = links["next"]
                        parsed_query = parse_qs(urlparse(next_url).query)
                        next_cursor = parsed_query.get("cursor", [None])[0]
                    
                    output_data = {
                        "ts": datetime.utcnow().isoformat(),
                        "blogPosts": blog_posts,
                        "nextCursor": next_cursor,
                    }
                    output_str = json.dumps(output_data)
                    return ToolResult(success=True, output=output_str, data=output_data)
                else:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"API error: {response.status_code} - {response.text}",
                    )
                    
        except httpx.RequestError as e:
            return ToolResult(success=False, output="", error=f"Request error: {str(e)}")
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")