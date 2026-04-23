from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class YouTubeVideoCategoriesTool(BaseTool):
    name = "youtube_video_categories"
    description = "Get a list of video categories available on YouTube. Use this to discover valid category IDs for filtering search and trending results."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="YOUTUBE_API_KEY",
                description="YouTube API Key",
                env_var="YOUTUBE_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_api_key(self, context: dict | None) -> str:
        return (context.get("YOUTUBE_API_KEY") if context else None) or ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "regionCode": {
                    "type": "string",
                    "description": "ISO 3166-1 alpha-2 country code to get categories for (e.g., \"US\", \"GB\", \"JP\"). Defaults to US.",
                },
                "hl": {
                    "type": "string",
                    "description": "Language for category titles (ISO 639-1 code, e.g., \"en\", \"es\", \"fr\"). Defaults to English.",
                }
            },
            "required": []
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = await self._resolve_api_key(context)
        
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="YouTube API key not configured.")
        
        headers = {
            "Content-Type": "application/json",
        }
        
        url = "https://www.googleapis.com/youtube/v3/videoCategories"
        region_code = parameters.get("regionCode", "US")
        hl = parameters.get("hl")
        query_params = {
            "part": "snippet",
            "key": api_key,
            "regionCode": region_code,
        }
        if hl:
            query_params["hl"] = hl
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)
                
                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    if "error" in data:
                        error_msg = data["error"].get("message", "Failed to fetch video categories")
                        return ToolResult(success=False, output="", error=error_msg)
                    
                    items_raw = data.get("items", [])
                    items = []
                    for item in items_raw:
                        snippet = item.get("snippet", {})
                        assignable = snippet.get("assignable")
                        if assignable is not False:
                            items.append({
                                "categoryId": item.get("id", ""),
                                "title": snippet.get("title", ""),
                                "assignable": assignable or False,
                            })
                    
                    transformed = {
                        "items": items,
                        "totalResults": len(items),
                    }
                    output_str = json.dumps(transformed)
                    return ToolResult(success=True, output=output_str, data=transformed)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")