from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class WordPressSearchContentTool(BaseTool):
    name = "wordpress_search_content"
    description = "Search across all content types in WordPress.com (posts, pages, media)"
    category = "integration"

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

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "siteId": {
                    "type": "string",
                    "description": "WordPress.com site ID or domain (e.g., 12345678 or mysite.wordpress.com)",
                },
                "query": {
                    "type": "string",
                    "description": "Search query",
                },
                "perPage": {
                    "type": "number",
                    "description": "Number of results per request (default: 10, max: 100)",
                },
                "page": {
                    "type": "number",
                    "description": "Page number for pagination",
                },
                "type": {
                    "type": "string",
                    "description": "Filter by content type: post, page, attachment",
                },
                "subtype": {
                    "type": "string",
                    "description": "Filter by post type slug (e.g., post, page)",
                },
            },
            "required": ["siteId", "query"],
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
        query = parameters["query"]
        per_page = parameters.get("perPage")
        page_num = parameters.get("page")
        content_type = parameters.get("type")
        subtype = parameters.get("subtype")
        
        url = f"https://public-api.wordpress.com/rest/v1.1/{site_id}/search"
        
        params: Dict[str, Any] = {
            "search": query,
        }
        if per_page is not None:
            params["per_page"] = per_page
        if page_num is not None:
            params["page"] = page_num
        if content_type is not None:
            params["type"] = content_type
        if subtype is not None:
            params["subtype"] = subtype
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params)
                
                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    total = int(response.headers.get("X-WP-Total", "0"))
                    total_pages = int(response.headers.get("X-WP-TotalPages", "0"))
                    results = [
                        {
                            "id": result["id"],
                            "title": result["title"],
                            "url": result["url"],
                            "type": result["type"],
                            "subtype": result.get("subtype"),
                        }
                        for result in data
                    ]
                    output_data = {
                        "results": results,
                        "total": total,
                        "totalPages": total_pages,
                    }
                    return ToolResult(success=True, output=str(output_data), data=output_data)
                else:
                    error_text = response.text
                    error_msg = error_text
                    try:
                        error_json = response.json()
                        error_msg = error_json.get("message", error_text)
                    except Exception:
                        pass
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")