from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class WordPressListCommentsTool(BaseTool):
    name = "wordpress_list_comments"
    description = "List comments from WordPress.com with optional filters"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="WORDPRESS_ACCESS_TOKEN",
                description="Access token",
                env_var="WORDPRESS_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "wordpress",
            context=context,
            context_token_keys=("provider_token",),
            env_token_keys=("WORDPRESS_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "siteId": {
                    "type": "string",
                    "description": "WordPress.com site ID or domain (e.g., 12345678 or mysite.wordpress.com)",
                },
                "perPage": {
                    "type": "number",
                    "description": "Number of comments per request (e.g., 10, 25, 50). Default: 10, max: 100",
                },
                "page": {
                    "type": "number",
                    "description": "Page number for pagination (e.g., 1, 2, 3)",
                },
                "postId": {
                    "type": "number",
                    "description": "Filter by post ID (e.g., 123, 456)",
                },
                "status": {
                    "type": "string",
                    "description": "Filter by comment status: approved, hold, spam, trash",
                },
                "search": {
                    "type": "string",
                    "description": "Search term to filter comments (e.g., \"question\", \"feedback\")",
                },
                "orderBy": {
                    "type": "string",
                    "description": "Order by field: date, id, parent",
                },
                "order": {
                    "type": "string",
                    "description": "Order direction: asc or desc",
                },
            },
            "required": ["siteId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        params: Dict[str, str] = {}
        if "perPage" in parameters:
            params["per_page"] = str(parameters["perPage"])
        if "page" in parameters:
            params["page"] = str(parameters["page"])
        if "postId" in parameters:
            params["post"] = str(parameters["postId"])
        if "status" in parameters:
            params["status"] = parameters["status"]
        if "search" in parameters:
            params["search"] = parameters["search"]
        if "orderBy" in parameters:
            params["orderby"] = parameters["orderBy"]
        if "order" in parameters:
            params["order"] = parameters["order"]
        
        url = f"https://public-api.wordpress.com/rest/v1.1/{parameters['siteId']}/comments"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params)
                
                if response.status_code in [200]:
                    try:
                        data = response.json()
                    except Exception:
                        data = []
                    
                    total = int(response.headers.get("X-WP-Total", "0"))
                    total_pages = int(response.headers.get("X-WP-TotalPages", "0"))
                    
                    comments = []
                    for comment in data:
                        comments.append({
                            "id": comment.get("id"),
                            "post": comment.get("post"),
                            "parent": comment.get("parent"),
                            "author": comment.get("author"),
                            "author_name": comment.get("author_name"),
                            "author_email": comment.get("author_email"),
                            "author_url": comment.get("author_url"),
                            "date": comment.get("date"),
                            "content": comment.get("content"),
                            "link": comment.get("link"),
                            "status": comment.get("status"),
                        })
                    
                    result = {
                        "comments": comments,
                        "total": total,
                        "totalPages": total_pages,
                    }
                    import json
                    return ToolResult(success=True, output=json.dumps(result), data=result)
                else:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("message", response.text)
                    except Exception:
                        error_msg = response.text
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")