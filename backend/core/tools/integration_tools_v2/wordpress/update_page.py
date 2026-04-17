from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class WordPressUpdatePageTool(BaseTool):
    name = "wordpress_update_page"
    description = "Update an existing page in WordPress.com"
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
            context_token_keys=("wordpress_token",),
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
                "pageId": {
                    "type": "integer",
                    "description": "The ID of the page to update",
                },
                "title": {
                    "type": "string",
                    "description": "Page title",
                },
                "content": {
                    "type": "string",
                    "description": "Page content (HTML or plain text)",
                },
                "status": {
                    "type": "string",
                    "description": "Page status: publish, draft, pending, private",
                },
                "excerpt": {
                    "type": "string",
                    "description": "Page excerpt",
                },
                "parent": {
                    "type": "integer",
                    "description": "Parent page ID for hierarchical pages",
                },
                "menuOrder": {
                    "type": "integer",
                    "description": "Order in page menu",
                },
                "featuredMedia": {
                    "type": "integer",
                    "description": "Featured image media ID",
                },
                "slug": {
                    "type": "string",
                    "description": "URL slug for the page",
                },
            },
            "required": ["siteId", "pageId"],
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
        page_id = parameters["pageId"]
        url = f"https://public-api.wordpress.com/rest/v1/{site_id}/pages/{page_id}"

        body: Dict[str, Any] = {}
        for field, body_field in [
            ("title", "title"),
            ("content", "content"),
            ("status", "status"),
            ("excerpt", "excerpt"),
            ("slug", "slug"),
        ]:
            val = parameters.get(field)
            if val:
                body[body_field] = val
        for field, body_field in [
            ("parent", "parent"),
            ("menuOrder", "menu_order"),
            ("featuredMedia", "featured_media"),
        ]:
            if field in parameters:
                body[body_field] = parameters[field]

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")