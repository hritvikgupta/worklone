from typing import Any, Dict
import httpx
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class HubspotUpdateCompanyTool(BaseTool):
    name = "hubspot_update_company"
    description = "Update an existing company in HubSpot by ID or domain"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="HUBSPOT_ACCESS_TOKEN",
                description="Access token",
                env_var="HUBSPOT_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "hubspot",
            context=context,
            context_token_keys=("provider_token",),
            env_token_keys=("HUBSPOT_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "companyId": {
                    "type": "string",
                    "description": "The HubSpot company ID (numeric string) or domain of the company to update",
                },
                "idProperty": {
                    "type": "string",
                    "description": 'Property to use as unique identifier (e.g., "domain"). If not specified, uses record ID',
                },
                "properties": {
                    "type": "object",
                    "description": 'Company properties to update as JSON object (e.g., {"name": "New Name", "industry": "Finance"})',
                },
            },
            "required": ["companyId", "properties"],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        company_id = parameters["companyId"].strip()
        url = f"https://api.hubapi.com/crm/v3/objects/companies/{company_id}"
        id_property = parameters.get("idProperty")
        if id_property:
            url += f"?idProperty={id_property}"
        
        body = {
            "properties": parameters["properties"],
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")