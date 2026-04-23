from typing import Any, Dict
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class PipedriveUpdateDealTool(BaseTool):
    name = "pipedrive_update_deal"
    description = "Update an existing deal in Pipedrive"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="PIPEDRIVE_ACCESS_TOKEN",
                description="Access token for the Pipedrive API",
                env_var="PIPEDRIVE_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "pipedrive",
            context=context,
            context_token_keys=("provider_token",),
            env_token_keys=("PIPEDRIVE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "deal_id": {
                    "type": "string",
                    "description": "The ID of the deal to update (e.g., \"123\")",
                },
                "title": {
                    "type": "string",
                    "description": "New title for the deal (e.g., \"Updated Enterprise License\")",
                },
                "value": {
                    "type": "string",
                    "description": "New monetary value for the deal (e.g., \"7500\")",
                },
                "status": {
                    "type": "string",
                    "description": "New status: open, won, lost",
                },
                "stage_id": {
                    "type": "string",
                    "description": "New stage ID for the deal (e.g., \"3\")",
                },
                "expected_close_date": {
                    "type": "string",
                    "description": "New expected close date in YYYY-MM-DD format (e.g., \"2025-07-15\")",
                },
            },
            "required": ["deal_id"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        
        deal_id = parameters.get("deal_id")
        if not deal_id:
            return ToolResult(success=False, output="", error="deal_id is required.")
        
        url = f"https://api.pipedrive.com/api/v2/deals/{deal_id}"
        
        body = {}
        title = parameters.get("title")
        if title:
            body["title"] = title
        value_str = parameters.get("value")
        if value_str:
            body["value"] = float(value_str)
        status = parameters.get("status")
        if status:
            body["status"] = status
        stage_id_str = parameters.get("stage_id")
        if stage_id_str:
            body["stage_id"] = int(stage_id_str)
        expected_close_date = parameters.get("expected_close_date")
        if expected_close_date:
            body["expected_close_date"] = expected_close_date
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    try:
                        data = response.json()
                        if data.get("success"):
                            return ToolResult(success=True, output=response.text, data=data)
                        else:
                            error_msg = data.get("error", "Failed to update deal in Pipedrive")
                            return ToolResult(success=False, output="", error=error_msg)
                    except:
                        return ToolResult(success=True, output=response.text, data={})
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")