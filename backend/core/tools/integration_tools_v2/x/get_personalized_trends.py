from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class XGetPersonalizedTrendsTool(BaseTool):
    name = "x_get_personalized_trends"
    description = "Get personalized trending topics for the authenticated user"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="X_ACCESS_TOKEN",
                description="X OAuth access token",
                env_var="X_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "x",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("X_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {},
            "required": []
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = "https://api.x.com/2/users/personalized_trends?personalized_trend.fields=category,post_count,trend_name,trending_since"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    if not data.get("data") or not isinstance(data["data"], list):
                        errors = data.get("errors", [])
                        error_msg = errors[0].get("detail") if errors else "No personalized trends found or invalid response"
                        return ToolResult(success=False, output="", error=error_msg)
                    
                    def _transform_personalized_trend(trend: dict) -> dict:
                        return {
                            "trendName": trend.get("trend_name"),
                            "postCount": trend.get("post_count"),
                            "category": trend.get("category"),
                            "trendingSince": trend.get("trending_since"),
                        }
                    
                    trends = [_transform_personalized_trend(trend) for trend in data["data"]]
                    structured_data = {"trends": trends}
                    return ToolResult(success=True, output=str(structured_data), data=structured_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")