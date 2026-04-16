from typing import Any, Dict
import httpx
import json
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class WordPressListCategoriesTool(BaseTool):
    name = "wordpress_list_categories"
    description = "List categories from WordPress.com"
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
                    "description": "Number of categories per request (e.g., 10, 25, 50). Default: 10, max: 100",
                },
                "page": {
                    "type": "number",
                    "description": "Page number for pagination (e.g., 1, 2, 3)",
                },
                "search": {
                    "type": "string",
                    "description": "Search term to filter categories (e.g., \"news\", \"technology\")",
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

        site_id = parameters["siteId"]
        url = f"https://public-api.wordpress.com/rest/v1.1/sites/{site_id}/categories"

        params_dict: dict[str, Any] = {}
        for key, query_key in [
            ("perPage", "per_page"),
            ("page", "page"),
            ("search", "search"),
            ("order", "order"),
        ]:
            value = parameters.get(key)
            if value is not None:
                params_dict[query_key] = value

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params_dict)

                if response.status_code == 200:
                    data = response.json()
                    total_str = response.headers.get("X-WP-Total")
                    total = int(total_str) if total_str else 0
                    total_pages_str = response.headers.get("X-WP-TotalPages")
                    total_pages = int(total_pages_str) if total_pages_str else 0

                    categories = []
                    for cat in data:
                        categories.append({
                            "id": cat["id"],
                            "count": cat["count"],
                            "description": cat["description"],
                            "link": cat["link"],
                            "name": cat["name"],
                            "slug": cat["slug"],
                            "taxonomy": cat["taxonomy"],
                            "parent": cat["parent"],
                        })

                    transformed = {
                        "categories": categories,
                        "total": total,
                        "totalPages": total_pages,
                    }
                    output_str = json.dumps(transformed)
                    return ToolResult(success=True, output=output_str, data=transformed)
                else:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("message", f"WordPress API error: {response.status_code}")
                    except Exception:
                        error_msg = f"WordPress API error: {response.status_code}"
                    return ToolResult(success=False, output="", error=error_msg)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")