from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class PipedriveUpdateLeadTool(BaseTool):
    name = "pipedrive_update_lead"
    description = "Update an existing lead in Pipedrive"
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
                "lead_id": {
                    "type": "string",
                    "description": "The ID of the lead to update (e.g., \"abc123-def456-ghi789\")",
                },
                "title": {
                    "type": "string",
                    "description": "New name for the lead (e.g., \"Updated Lead - Premium Package\")",
                },
                "person_id": {
                    "type": "string",
                    "description": "New person ID (e.g., \"456\")",
                },
                "organization_id": {
                    "type": "string",
                    "description": "New organization ID (e.g., \"789\")",
                },
                "owner_id": {
                    "type": "string",
                    "description": "New owner user ID (e.g., \"123\")",
                },
                "value_amount": {
                    "type": "string",
                    "description": "New value amount (e.g., \"15000\")",
                },
                "value_currency": {
                    "type": "string",
                    "description": "New currency code (e.g., \"USD\", \"EUR\", \"GBP\")",
                },
                "expected_close_date": {
                    "type": "string",
                    "description": "New expected close date in YYYY-MM-DD format (e.g., \"2025-05-01\")",
                },
                "is_archived": {
                    "type": "string",
                    "description": "Archive the lead: true or false",
                },
            },
            "required": ["lead_id"],
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
        
        lead_id = parameters["lead_id"]
        url = f"https://api.pipedrive.com/v1/leads/{lead_id}"
        
        body: Dict[str, Any] = {}
        title = parameters.get("title")
        if title:
            body["title"] = title
        person_id = parameters.get("person_id")
        if person_id:
            body["person_id"] = int(person_id)
        organization_id = parameters.get("organization_id")
        if organization_id:
            body["organization_id"] = int(organization_id)
        owner_id = parameters.get("owner_id")
        if owner_id:
            body["owner_id"] = int(owner_id)
        value_amount = parameters.get("value_amount")
        value_currency = parameters.get("value_currency")
        if value_amount and value_currency:
            body["value"] = {
                "amount": int(value_amount),
                "currency": value_currency,
            }
        expected_close_date = parameters.get("expected_close_date")
        if expected_close_date:
            body["expected_close_date"] = expected_close_date
        is_archived = parameters.get("is_archived")
        if is_archived:
            body["is_archived"] = is_archived == "true"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")