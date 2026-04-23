from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class XGetTrendsByWoeidTool(BaseTool):
    name = "x_get_trends_by_woeid"
    description = "Get trending topics for a specific location by WOEID (e.g., 1 for worldwide, 23424977 for US)"
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
            "properties": {
                "woeid": {
                    "type": "string",
                    "description": 'Yahoo Where On Earth ID (e.g., "1" for worldwide, "23424977" for US, "23424975" for UK)',
                },
                "maxTrends": {
                    "type": "number",
                    "description": "Maximum number of trends to return (1-50, default 20)",
                },
            },
            "required": ["woeid"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        woeid = parameters["woeid"].strip()
        query_params = {
            "trend.fields": "trend_name,tweet_count",
        }
        max_trends = parameters.get("maxTrends")
        if max_trends is not None:
            query_params["max_trends"] = int(max_trends)
        
        url = f"https://api.x.com/2/trends/by/woeid/{woeid}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")