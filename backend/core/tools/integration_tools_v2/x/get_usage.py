from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class XGetUsageTool(BaseTool):
    name = "x_get_usage"
    description = "Get the API usage data for your X project"
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
            context_token_keys=("access_token",),
            env_token_keys=("X_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "days": {
                    "type": "number",
                    "description": "Number of days of usage data to return (1-90, default 7)",
                }
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        query_params = {
            "usage.fields": "cap_reset_day,daily_client_app_usage,daily_project_usage,project_cap,project_id,project_usage",
        }
        days = parameters.get("days")
        if days is not None:
            query_params["days"] = int(days)
        
        url = "https://api.x.com/2/usage/tweets"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)
                
                if response.status_code not in [200, 201, 204]:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                
                if not data.get("data"):
                    errors = data.get("errors", [])
                    error_msg = next((e.get("detail") for e in errors), "Failed to get usage data")
                    return ToolResult(success=False, output="", error=error_msg)
                
                output_data = {
                    "capResetDay": data["data"].get("cap_reset_day"),
                    "projectId": str(data["data"].get("project_id", "")),
                    "projectCap": data["data"].get("project_cap"),
                    "projectUsage": data["data"].get("project_usage"),
                    "dailyProjectUsage": [
                        {
                            "date": u["date"],
                            "usage": u.get("usage", 0),
                        }
                        for u in data["data"].get("daily_project_usage", {}).get("usage", [])
                    ],
                    "dailyClientAppUsage": [
                        {
                            "clientAppId": str(app.get("client_app_id", "")),
                            "usage": [
                                {
                                    "date": u["date"],
                                    "usage": u.get("usage", 0),
                                }
                                for u in app.get("usage", [])
                            ],
                        }
                        for app in data["data"].get("daily_client_app_usage", [])
                    ],
                }
                return ToolResult(success=True, output=response.text, data=output_data)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")