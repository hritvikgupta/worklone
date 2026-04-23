from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class PipedriveCreateDealTool(BaseTool):
    name = "pipedrive_create_deal"
    description = "Create a new deal in Pipedrive"
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
                "title": {
                    "type": "string",
                    "description": "The title of the deal (e.g., \"Enterprise Software License\")",
                },
                "value": {
                    "type": "string",
                    "description": "The monetary value of the deal (e.g., \"5000\")",
                },
                "currency": {
                    "type": "string",
                    "description": "Currency code (e.g., \"USD\", \"EUR\", \"GBP\")",
                },
                "person_id": {
                    "type": "string",
                    "description": "ID of the person this deal is associated with (e.g., \"456\")",
                },
                "org_id": {
                    "type": "string",
                    "description": "ID of the organization this deal is associated with (e.g., \"789\")",
                },
                "pipeline_id": {
                    "type": "string",
                    "description": "ID of the pipeline this deal should be placed in (e.g., \"1\")",
                },
                "stage_id": {
                    "type": "string",
                    "description": "ID of the stage this deal should be placed in (e.g., \"2\")",
                },
                "status": {
                    "type": "string",
                    "description": "Status of the deal: open, won, lost",
                },
                "expected_close_date": {
                    "type": "string",
                    "description": "Expected close date in YYYY-MM-DD format (e.g., \"2025-06-30\")",
                },
            },
            "required": ["title"],
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
        
        url = "https://api.pipedrive.com/api/v2/deals"
        
        body = {"title": parameters["title"]}
        numeric_fields = {"value", "person_id", "org_id", "pipeline_id", "stage_id"}
        for k, v in parameters.items():
            if k == "title" or not v:
                continue
            if k in numeric_fields:
                try:
                    body[k] = float(v)
                except ValueError:
                    continue
            else:
                body[k] = v
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201]:
                    data = response.json()
                    if data.get("success"):
                        return ToolResult(success=True, output=str(data.get("data", {})), data=data)
                    else:
                        return ToolResult(
                            success=False, output="", error=data.get("error", response.text)
                        )
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")