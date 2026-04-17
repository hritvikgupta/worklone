from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class WordPressListMediaTool(BaseTool):
    name = "wordpress_list_media"
    description = "List media items from the WordPress.com media library"
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
                    "description": "Number of media items per request (e.g., 10, 25, 50). Default: 10, max: 100",
                },
                "page": {
                    "type": "number",
                    "description": "Page number for pagination (e.g., 1, 2, 3)",
                },
                "search": {
                    "type": "string",
                    "description": 'Search term to filter media (e.g., "logo", "banner")',
                },
                "mediaType": {
                    "type": "string",
                    "description": "Filter by media type: image, video, audio, application",
                },
                "mimeType": {
                    "type": "string",
                    "description": "Filter by specific MIME type (e.g., image/jpeg, image/png)",
                },
                "orderBy": {
                    "type": "string",
                    "description": "Order by field: date, id, title, slug",
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
        url = f"https://public-api.wordpress.com/rest/v1/{site_id}/media"
        
        query_params: Dict[str, Any] = {}
        if parameters.get("perPage") is not None:
            query_params["per_page"] = parameters["perPage"]
        if parameters.get("page") is not None:
            query_params["page"] = parameters["page"]
        if parameters.get("search") is not None:
            query_params["search"] = parameters["search"]
        if parameters.get("mediaType") is not None:
            query_params["media_type"] = parameters["mediaType"]
        if parameters.get("mimeType") is not None:
            query_params["mime_type"] = parameters["mimeType"]
        if parameters.get("orderBy") is not None:
            query_params["orderby"] = parameters["orderBy"]
        if parameters.get("order") is not None:
            query_params["order"] = parameters["order"]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)
                
                if response.status_code not in [200]:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("message", f"WordPress API error: {response.status_code}")
                    except Exception:
                        error_msg = response.text
                    return ToolResult(success=False, output="", error=error_msg)
                
                try:
                    raw_data = response.json()
                except Exception:
                    return ToolResult(success=False, output=response.text, error="Invalid JSON response")
                
                total = int(response.headers.get("X-WP-Total", "0"))
                total_pages = int(response.headers.get("X-WP-TotalPages", "0"))
                
                media_items = []
                for item in raw_data:
                    media_items.append({
                        "id": item.get("id"),
                        "date": item.get("date"),
                        "slug": item.get("slug"),
                        "type": item.get("type"),
                        "link": item.get("link"),
                        "title": item.get("title"),
                        "caption": item.get("caption"),
                        "alt_text": item.get("alt_text"),
                        "media_type": item.get("media_type"),
                        "mime_type": item.get("mime_type"),
                        "source_url": item.get("source_url"),
                        "media_details": item.get("media_details"),
                    })
                
                result_data = {
                    "media": media_items,
                    "total": total,
                    "totalPages": total_pages,
                }
                
                return ToolResult(
                    success=True,
                    output=json.dumps(result_data),
                    data=result_data
                )
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")