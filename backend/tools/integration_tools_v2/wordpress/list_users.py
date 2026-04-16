from typing import Any, Dict
import httpx
import json
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class WordPressListUsersTool(BaseTool):
    name = "wordpress_list_users"
    description = "List users from WordPress.com (requires admin privileges)"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="WORDPRESS_ACCESS_TOKEN",
                description="WordPress.com OAuth access token",
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
                    "description": "Number of users per request (e.g., 10, 25, 50). Default: 10, max: 100",
                },
                "page": {
                    "type": "number",
                    "description": "Page number for pagination (e.g., 1, 2, 3)",
                },
                "search": {
                    "type": "string",
                    "description": "Search term to filter users (e.g., \"john\", \"admin\")",
                },
                "roles": {
                    "type": "string",
                    "description": "Comma-separated role names to filter by (e.g., \"administrator,editor\")",
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
        
        site_id = parameters.get("siteId")
        if not site_id:
            return ToolResult(success=False, output="", error="siteId is required.")
        
        query_params: Dict[str, Any] = {}
        optional_mappings = {
            "perPage": "per_page",
            "page": "page",
            "search": "search",
            "roles": "roles",
            "order": "order",
        }
        for param_key, query_key in optional_mappings.items():
            if param_key in parameters:
                val = parameters[param_key]
                if val is not None:
                    query_params[query_key] = val
        
        url = f"https://public-api.wordpress.com/rest/v1/{site_id}/users"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)
                
                if response.status_code == 200:
                    data = response.json()
                    total = int(response.headers.get("X-WP-Total", "0"))
                    total_pages = int(response.headers.get("X-WP-TotalPages", "0"))
                    
                    users = []
                    for user in data:
                        mapped_user = {
                            "id": user.get("id"),
                            "username": user.get("username"),
                            "name": user.get("name"),
                            "first_name": user.get("first_name"),
                            "last_name": user.get("last_name"),
                            "email": user.get("email"),
                            "url": user.get("url"),
                            "description": user.get("description"),
                            "link": user.get("link"),
                            "slug": user.get("slug"),
                            "roles": user.get("roles", []),
                            "avatar_urls": user.get("avatar_urls"),
                        }
                        users.append(mapped_user)
                    
                    output_data = {
                        "users": users,
                        "total": total,
                        "totalPages": total_pages,
                    }
                    return ToolResult(success=True, output=json.dumps(output_data), data=output_data)
                else:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("message", f"WordPress API error: {response.status_code}")
                    except:
                        error_msg = response.text or f"WordPress API error: {response.status_code}"
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")