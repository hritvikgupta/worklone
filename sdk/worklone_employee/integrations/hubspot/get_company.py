from typing import Any, Dict
import httpx
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class HubspotGetCompanyTool(BaseTool):
    name = "hubspot_get_company"
    description = "Retrieve a single company by ID or domain from HubSpot"
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
            context_token_keys=("accessToken",),
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
                    "description": "The HubSpot company ID (numeric string) or domain to retrieve",
                },
                "idProperty": {
                    "type": "string",
                    "description": 'Property to use as unique identifier (e.g., "domain"). If not specified, uses record ID',
                },
                "properties": {
                    "type": "string",
                    "description": 'Comma-separated list of HubSpot property names to return (e.g., "name,domain,industry")',
                },
                "associations": {
                    "type": "string",
                    "description": 'Comma-separated list of object types to retrieve associated IDs for (e.g., "contacts,deals")',
                },
            },
            "required": ["companyId"],
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

        params: dict[str, str] = {}
        if id_property := parameters.get("idProperty"):
            params["idProperty"] = id_property
        if properties := parameters.get("properties"):
            params["properties"] = properties
        if associations := parameters.get("associations"):
            params["associations"] = associations

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")