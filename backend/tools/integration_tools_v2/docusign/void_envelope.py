from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class DocuSignVoidEnvelopeTool(BaseTool):
    name = "docusign_void_envelope"
    description = "Void (cancel) a sent DocuSign envelope that has not yet been completed"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="DOCUSIGN_ACCESS_TOKEN",
                description="DocuSign OAuth access token",
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

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "envelopeId": {
                    "type": "string",
                    "description": "The envelope ID to void",
                },
                "voidedReason": {
                    "type": "string",
                    "description": "Reason for voiding the envelope",
                },
            },
            "required": ["envelopeId", "voidedReason"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        auth_header = {"Authorization": f"Bearer {access_token}"}
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Fetch user accounts to get account_id and base_uri
                userinfo_url = "https://account-d.docusign.com/oauth/userinfo"
                userinfo_response = await client.get(userinfo_url, headers=auth_header)
                
                if userinfo_response.status_code != 200:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Failed to fetch user accounts: {userinfo_response.status_code} - {userinfo_response.text}",
                    )
                
                userinfo = userinfo_response.json()
                accounts = userinfo.get("accounts", [])
                if not accounts:
                    return ToolResult(
                        success=False, output="", error="No DocuSign accounts found for this user."
                    )
                
                # Prefer default account, fallback to first
                default_account = next(
                    (acc for acc in accounts if acc.get("is_default")), accounts[0]
                )
                account_id = default_account["account_id"]
                base_uri = default_account["base_uri"].rstrip("/")
                
                # Void the envelope
                envelope_id = parameters["envelopeId"]
                voided_reason = parameters["voidedReason"]
                url = f"{base_uri}/restapi/v2.1/accounts/{account_id}/envelopes/{envelope_id}"
                
                void_headers = {**auth_header, "Content-Type": "application/json"}
                body = {
                    "status": "voided",
                    "voidedReason": voided_reason,
                }
                
                void_response = await client.put(url, headers=void_headers, json=body)
                
                if void_response.status_code == 204:
                    return ToolResult(
                        success=True,
                        output="Envelope voided successfully.",
                        data={
                            "envelopeId": envelope_id,
                            "status": "voided",
                        },
                    )
                else:
                    error_msg = void_response.text
                    try:
                        err_data = void_response.json()
                        error_msg = (
                            err_data.get("errorMessage")
                            or err_data.get("message", error_msg)
                            or error_msg
                        )
                    except ValueError:
                        pass
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Failed to void envelope ({void_response.status_code}): {error_msg}",
                    )
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")