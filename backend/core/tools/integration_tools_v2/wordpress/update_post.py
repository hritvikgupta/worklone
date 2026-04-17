from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class WordPressUpdatePostTool(BaseTool):
    name = "wordpress_update_post"
    description = "Update an existing blog post in WordPress.com"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="WORDPRESS_ACCESS_TOKEN",
                description="WordPress.com access token",
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
                "postId": {
                    "type": "number",
                    "description": "The ID of the post to update",
                },
                "title": {
                    "type": "string",
                    "description": "Post title",
                },
                "content": {
                    "type": "string",
                    "description": "Post content (HTML or plain text)",
                },
                "status": {
                    "type": "string",
                    "description": "Post status: publish, draft, pending, private, or future",
                },
                "excerpt": {
                    "type": "string",
                    "description": "Post excerpt",
                },
                "categories": {
                    "type": "string",
                    "description": "Comma-separated category IDs",
                },
                "tags": {
                    "type": "string",
                    "description": "Comma-separated tag IDs",
                },
                "featuredMedia": {
                    "type": "number",
                    "description": "Featured image media ID",
                },
                "slug": {
                    "type": "string",
                    "description": "URL slug for the post",
                },
            },
            "required": ["siteId", "postId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        site_id = parameters["siteId"]
        post_id = parameters["postId"]
        url = f"https://public-api.wordpress.com/rest/v1/{site_id}/posts/{post_id}"

        body: Dict[str, Any] = {}
        title = parameters.get("title")
        if title:
            body["title"] = title
        content = parameters.get("content")
        if content:
            body["content"] = content
        status = parameters.get("status")
        if status:
            body["status"] = status
        excerpt = parameters.get("excerpt")
        if excerpt:
            body["excerpt"] = excerpt
        slug = parameters.get("slug")
        if slug:
            body["slug"] = slug
        featured_media = parameters.get("featuredMedia")
        if featured_media is not None:
            body["featured_media"] = featured_media
        categories = parameters.get("categories")
        if categories:
            cat_ids: list[int] = []
            for cat_str in str(categories).split(","):
                cat_str = cat_str.strip()
                if cat_str and cat_str.isdigit():
                    cat_ids.append(int(cat_str))
            if cat_ids:
                body["categories"] = cat_ids
        tags = parameters.get("tags")
        if tags:
            tag_ids: list[int] = []
            for tag_str in str(tags).split(","):
                tag_str = tag_str.strip()
                if tag_str and tag_str.isdigit():
                    tag_ids.append(int(tag_str))
            if tag_ids:
                body["tags"] = tag_ids

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")