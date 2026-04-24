from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class PipedriveCreateLeadTool(BaseTool):
    name = "pipedrive_create_lead"
    description = "Create a new lead in Pipedrive"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="PIPEDRIVE_ACCESS_TOKEN",
                description="Access token",
                env_var="PIPEDRIVE_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "pipedrive",
            context=context,
            context_token_keys=("access_token",),
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
                    "description": 'The name of the lead (e.g., "Acme Corp - Website Redesign")',
                },
                "person_id": {
                    "type": "string",
                    "description": 'ID of the person (REQUIRED unless organization_id is provided) (e.g., "456")',
                },
                "organization_id": {
                    "type": "string",
                    "description": 'ID of the organization (REQUIRED unless person_id is provided) (e.g., "789")',
                },
                "owner_id": {
                    "type": "string",
                    "description": 'ID of the user who will own the lead (e.g., "123")',
                },
                "value_amount": {
                    "type": "string",
                    "description": 'Potential value amount (e.g., "10000")',
                },
                "value_currency": {
                    "type": "string",
                    "description": 'Currency code (e.g., "USD", "EUR", "GBP")',
                },
                "expected_close_date": {
                    "type": "string",
                    "description": 'Expected close date in YYYY-MM-DD format (e.g., "2025-04-15")',
                },
                "visible_to": {
                    "type": "string",
                    "description": 'Visibility: 1 (Owner & followers), 3 (Entire company)',
                },
            },
            "required": ["title"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        if not parameters.get("person_id") and not parameters.get("organization_id"):
            return ToolResult(
                success=False,
                output="",
                error="Either person_id or organization_id is required to create a lead",
            )

        body: Dict[str, Any] = {
            "title": parameters["title"],
        }

        if parameters.get("person_id"):
            body["person_id"] = int(parameters["person_id"])
        if parameters.get("organization_id"):
            body["organization_id"] = int(parameters["organization_id"])
        if parameters.get("owner_id"):
            body["owner_id"] = int(parameters["owner_id"])
        if parameters.get("value_amount") and parameters.get("value_currency"):
            body["value"] = {
                "amount": float(parameters["value_amount"]),
                "currency": parameters["value_currency"],
            }
        if parameters.get("expected_close_date"):
            body["expected_close_date"] = parameters["expected_close_date"]
        if parameters.get("visible_to"):
            body["visible_to"] = int(parameters["visible_to"])

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        url = "https://api.pipedrive.com/v1/leads"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    if not data.get("success"):
                        return ToolResult(
                            success=False,
                            output="",
                            error=data.get("error", "Failed to create lead in Pipedrive"),
                        )
                    return ToolResult(success=True, output=response.text, data=data)
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")