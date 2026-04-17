from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class WordPressListPagesTool(BaseTool):
    name = "wordpress_list_pages"
    description = "List pages from WordPress.com with optional filters"
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
                "perPage": {
                    "type": "number",
                    "description": "Number of pages per request (e.g., 10, 25, 50). Default: 10, max: 100",
                },
                "page": {
                    "type": "number",
                    "description": "Page number for pagination (e.g., 1, 2, 3)",
                },
                "status": {
                    "type": "string",
                    "description": "Page status filter: publish, draft, pending, private",
                },
                "parent": {
                    "type": "number",
                    "description": "Filter by parent page ID (e.g., 123)",
                },
                "search": {
                    "type": "string",
                    "description": "Search term to filter pages (e.g., \"about\", \"contact\")",
                },
                "orderBy": {
                    "type": "string",
                    "description": "Order by field: date, id, title, slug, modified, menu_order",
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
        url = f"https://public-api.wordpress.com/rest/v1.1/sites/{site_id}/pages"
        
        query_params: Dict[str, Any] = {}
        param_mappings = [
            ("perPage", "per_page"),
            ("page", "page"),
            ("status", "status"),
            ("parent", "parent"),
            ("search", "search"),
            ("orderBy", "orderby"),
            ("order", "order"),
        ]
        for param_name, query_key in param_mappings:
            if param_name in parameters and parameters[param_name] is not None:
                query_params[query_key] = parameters[param_name]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)
                
                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    total = int(response.headers.get("X-WP-Total", 0))
                    total_pages = int(response.headers.get("X-WP-TotalPages", 0))
                    data["total"] = total
                    data["totalPages"] = total_pages
                    return ToolResult(success=True, output=response.text, data=data)
                else:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("message", response.text)
                    except Exception:
                        error_msg = response.text
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")