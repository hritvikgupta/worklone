from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class DocusignCreateFromTemplateTool(BaseTool):
    name = "docusign_create_from_template"
    description = "Create and send a DocuSign envelope using a pre-built template"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="DOCUSIGN_ACCESS_TOKEN",
                description="Access token",
                env_var="DOCUSIGN_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "docusign",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("DOCUSIGN_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    async def _get_account_info(self, access_token: str) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        for host in ["account-d.docusign.com", "account.docusign.com"]:
            url = f"https://{host}/oauth/userinfo"
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(url, headers=headers)
                    if response.status_code == 200:
                        data = response.json()
                        accounts = data.get("accounts", [])
                        if accounts:
                            default_account = next((acc for acc in accounts if acc.get("is_default", False)), accounts[0])
                            return {
                                "account_id": default_account["account_id"],
                                "base_url": default_account["base_uri"].rstrip("/"),
                            }
            except Exception:
                continue
        raise ValueError("Could not retrieve DocuSign account information.")

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "templateId": {
                    "type": "string",
                    "description": "DocuSign template ID to use",
                },
                "emailSubject": {
                    "type": "string",
                    "description": "Override email subject (uses template default if not set)",
                },
                "emailBody": {
                    "type": "string",
                    "description": "Override email body message",
                },
                "templateRoles": {
                    "type": "string",
                    "description": 'JSON array of template roles, e.g. [{"roleName":"Signer","name":"John","email":"john@example.com"}]',
                },
                "status": {
                    "type": "string",
                    "description": 'Envelope status: "sent" to send immediately, "created" for draft (default: "sent")',
                },
            },
            "required": ["templateId", "templateRoles"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        try:
            account_info = await self._get_account_info(access_token)
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Failed to retrieve account info: {str(e)}")
        
        try:
            template_roles = json.loads(parameters["templateRoles"])
        except json.JSONDecodeError as e:
            return ToolResult(success=False, output="", error=f"Invalid templateRoles JSON: {str(e)}")
        
        body = {
            "status": parameters.get("status", "sent"),
            "templateId": parameters["templateId"],
            "templateRoles": template_roles,
        }
        if parameters.get("emailSubject"):
            body["emailSubject"] = parameters["emailSubject"]
        if parameters.get("emailBody"):
            body["emailBlurb"] = parameters["emailBody"]
        
        url = f"{account_info['base_url']}/restapi/v2.1/accounts/{account_info['account_id']}/envelopes"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=f"API error {response.status_code}: {response.text}")
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")