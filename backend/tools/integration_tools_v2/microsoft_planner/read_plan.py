from typing import Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class MicrosoftPlannerReadPlanTool(BaseTool):
    name = "microsoft_planner_read_plan"
    description = "Get details of a specific Microsoft Planner plan"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="MICROSOFT_PLANNER_ACCESS_TOKEN",
                description="Access token for the Microsoft Planner API",
                env_var="MICROSOFT_PLANNER_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "microsoft-planner",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("MICROSOFT_PLANNER_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "planId": {
                    "type": "string",
                    "description": "The ID of the plan to retrieve (e.g., \"xqQg5FS2LkCe54tAMV_v2ZgADW2J\")",
                },
            },
            "required": ["planId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        plan_id = parameters.get("planId")
        if not plan_id:
            return ToolResult(success=False, output="", error="Plan ID is required")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        
        url = f"https://graph.microsoft.com/v1.0/planner/plans/{plan_id}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    plan = response.json()
                    metadata = {
                        "planId": plan.get("id"),
                        "planUrl": f"https://graph.microsoft.com/v1.0/planner/plans/{plan.get('id')}",
                    }
                    output_data = {
                        "plan": plan,
                        "metadata": metadata,
                    }
                    return ToolResult(success=True, output=response.text, data=output_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")