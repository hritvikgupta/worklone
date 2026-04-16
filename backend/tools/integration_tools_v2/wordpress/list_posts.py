from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class WordPressListPostsTool(BaseTool):
    name = "wordpress_list_posts"
    description = "List blog posts from WordPress.com with optional filters"
    category = "integration"
    BASE_URL: str = "https://public-api.wordpress.com/rest/v1.1"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="WORDPRESS_ACCESS_TOKEN",
                description="Access token for WordPress.com",
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

    def _build_query_params(self, parameters: dict) -> dict:
        query_params: dict = {}
        per_page = parameters.get("perPage")
        if per_page is not None:
            query_params["per_page"] = str(int(per_page))
        page_num = parameters.get("page")
        if page_num is not None:
            query_params["page"] = str(int(page_num))
        status = parameters.get("status")
        if status:
            query_params["status"] = status
        author = parameters.get("author")
        if author is not None:
            query_params["author"] = str(int(author))
        search_term = parameters.get("search")
        if search_term:
            query_params["search"] = search_term
        orderby = parameters.get("orderBy")
        if orderby:
            query_params["orderby"] = orderby
        order_dir = parameters.get("order")
        if order_dir:
            query_params["order"] = order_dir
        categories = parameters.get("categories")
        if categories:
            cat_ids = [cat_id.strip() for cat_id in str(categories).split(",") if cat_id.strip()]
            if cat_ids:
                query_params["categories"] = ",".join(cat_ids)
        tags = parameters.get("tags")
        if tags:
            tag_ids = [tag_id.strip() for tag_id in str(tags).split(",") if tag_id.strip()]
            if tag_ids:
                query_params["tags"] = ",".join(tag_ids)
        return query_params

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
                    "description": "Number of posts per page (e.g., 10, 25, 50). Default: 10, max: 100",
                },
                "page": {
                    "type": "number",
                    "description": "Page number for pagination (e.g., 1, 2, 3)",
                },
                "status": {
                    "type": "string",
                    "description": "Post status filter: publish, draft, pending, private",
                },
                "author": {
                    "type": "number",
                    "description": "Filter by author ID (e.g., 1, 42)",
                },
                "categories": {
                    "type": "string",
                    "description": "Comma-separated category IDs to filter by (e.g., \"1,2,3\")",
                },
                "tags": {
                    "type": "string",
                    "description": "Comma-separated tag IDs to filter by (e.g., \"5,10,15\")",
                },
                "search": {
                    "type": "string",
                    "description": "Search term to filter posts (e.g., \"tutorial\", \"announcement\")",
                },
                "orderBy": {
                    "type": "string",
                    "description": "Order by field: date, id, title, slug, modified",
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
        site_id = parameters["siteId"]
        query_params = self._build_query_params(parameters)
        url = f"{self.BASE_URL}/{site_id}/posts"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)
            if response.status_code == 200:
                total = int(response.headers.get("X-WP-Total", 0))
                total_pages = int(response.headers.get("X-WP-TotalPages", 0))
                posts_data = response.json()
                result_data = {
                    "posts": posts_data,
                    "total": total,
                    "totalPages": total_pages,
                }
                return ToolResult(success=True, output=response.text, data=result_data)
            else:
                error_content = response.text
                try:
                    error_json = response.json()
                    error_msg = error_json.get("message", str(error_json))
                except Exception:
                    error_msg = error_content
                return ToolResult(success=False, output="", error=error_msg)
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")