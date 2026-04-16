from typing import Any, Dict
import httpx
import json
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class HubspotCreateCompanyTool(BaseTool):
    name = "hubspot_create_company"
    description = "Create a new company in HubSpot"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="HUBSPOT_ACCESS_TOKEN",
                description="The access token for the HubSpot API",
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
                "properties": {
                    "type": "object",
                    "description": "Company properties as JSON object (e.g., {\"name\": \"Acme Inc\", \"domain\": \"acme.com\", \"industry\": \"Technology\"})",
                },
                "associations": {
                    "type": "array",
                    "description": "Array of associations to create with the company as JSON (each with \"to.id\" and \"types\" containing \"associationCategory\" and \"associationTypeId\")",
                },
            },
            "required": ["properties"],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = "https://api.hubapi.com/crm/v3/objects/companies"
        
        try:
            properties = parameters["properties"]
            if isinstance(properties, str):
                try:
                    properties = json.loads(properties)
                except json.JSONDecodeError:
                    return ToolResult(success=False, output="", error="Invalid JSON format for properties. Please provide a valid JSON object.")
            
            body = {"properties": properties}
            associations = parameters.get("associations")
            if associations and len(associations) > 0:
                body["associations"] = associations
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")