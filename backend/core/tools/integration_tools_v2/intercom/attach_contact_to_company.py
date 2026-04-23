from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class IntercomAttachContactToCompanyTool(BaseTool):
    name = "intercom_attach_contact_to_company"
    description = "Attach a contact to a company in Intercom"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="INTERCOM_ACCESS_TOKEN",
                description="Intercom API access token",
                env_var="INTERCOM_ACCESS_TOKEN",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "intercom",
            context=context,
            context_token_keys=("provider_token",),
            env_token_keys=("INTERCOM_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "contactId": {
                    "type": "string",
                    "description": "The ID of the contact to attach to the company",
                },
                "companyId": {
                    "type": "string",
                    "description": "The ID of the company to attach the contact to",
                },
            },
            "required": ["contactId", "companyId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Intercom-Version": "2.14",
        }
        
        url = f"https://api.intercom.io/contacts/{parameters['contactId']}/companies"
        body = {
            "id": parameters["companyId"],
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