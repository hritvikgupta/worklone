from typing import Any, Dict
import httpx
import base64
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class HubspotCreateListTool(BaseTool):
    name = "hubspot_create_list"
    description = "Create a new list in HubSpot. Specify the object type and processing type (MANUAL or DYNAMIC)"
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
            context_token_keys=("access_token",),
            env_token_keys=("HUBSPOT_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the list",
                },
                "objectTypeId": {
                    "type": "string",
                    "description": 'Object type ID (e.g., "0-1" for contacts, "0-2" for companies)',
                },
                "processingType": {
                    "type": "string",
                    "description": 'Processing type: "MANUAL" for static lists or "DYNAMIC" for active lists',
                },
            },
            "required": ["name", "objectTypeId", "processingType"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = "https://api.hubapi.com/crm/v3/lists"
        body = {
            "name": parameters["name"],
            "objectTypeId": parameters["objectTypeId"],
            "processingType": parameters["processingType"],
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")