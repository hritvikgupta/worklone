from typing import Any, Dict
import httpx
import base64
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class DocuSignListRecipientsTool(BaseTool):
    name = "docusign_list_recipient"
    description = "Get the recipient status details for a DocuSign envelope"
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

    def _decode_jwt_payload(self, token: str) -> Dict[str, Any]:
        try:
            parts = token.split(".")
            if len(parts) != 3:
                raise ValueError("Invalid JWT format")
            payload_b64 = parts[1]
            missing_padding = 4 - len(payload_b64) % 4
            if missing_padding:
                payload_b64 += "=" * missing_padding
            payload_bytes = base64.urlsafe_b64decode(payload_b64)
            payload = json.loads(payload_bytes.decode("utf-8"))
            return payload
        except json.JSONDecodeError:
            raise ValueError("Invalid JWT payload")
        except Exception as e:
            raise ValueError(f"Failed to decode JWT: {str(e)}")

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "envelopeId": {
                    "type": "string",
                    "description": "The envelope ID to get recipients for",
                },
            },
            "required": ["envelopeId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        envelope_id = parameters.get("envelopeId")
        if not envelope_id:
            return ToolResult(success=False, output="", error="Missing required parameter: envelopeId")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = self._decode_jwt_payload(access_token)
                iss = payload.get("iss")
                if not iss or "docusign.com" not in iss:
                    return ToolResult(
                        success=False,
                        output="",
                        error="Invalid DocuSign token issuer",
                    )
                
                userinfo_url = iss.rstrip("/") + "/userinfo"
                userinfo_headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                }
                userinfo_resp = await client.get(userinfo_url, headers=userinfo_headers)
                
                if userinfo_resp.status_code != 200:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Failed to fetch user info ({userinfo_resp.status_code}): {userinfo_resp.text}",
                    )
                
                userinfo = userinfo_resp.json()
                accounts = userinfo.get("accounts", [])
                if not accounts:
                    return ToolResult(
                        success=False,
                        output="",
                        error="No accounts found in userinfo",
                    )
                
                account = accounts[0]
                account_id = account["account_id"]
                base_uri = account["base_uri"].rstrip("/")
                
                recipients_url = f"{base_uri}/restapi/v2.1/accounts/{account_id}/envelopes/{envelope_id}/recipients"
                api_headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                }
                resp = await client.get(recipients_url, headers=api_headers)
                
                if resp.status_code != 200:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"DocuSign API error {resp.status_code}: {resp.text}",
                    )
                
                api_data = resp.json()
                recipients = api_data.get("recipients", [])
                
                signers = []
                carbon_copies = []
                for r in recipients:
                    rec_type = r.get("recipientType")
                    if rec_type == "signer":
                        signers.append({
                            "recipientId": r.get("recipientId"),
                            "name": r.get("name"),
                            "email": r.get("email"),
                            "status": r.get("status"),
                            "signedDateTime": r.get("signedDateTime"),
                            "deliveredDateTime": r.get("deliveredDateTime"),
                        })
                    elif rec_type == "carbonCopy":
                        carbon_copies.append({
                            "recipientId": r.get("recipientId"),
                            "name": r.get("name"),
                            "email": r.get("email"),
                            "status": r.get("status"),
                        })
                
                result = {
                    "signers": signers,
                    "carbonCopies": carbon_copies,
                }
                return ToolResult(
                    success=True,
                    output=json.dumps(result),
                    data=result,
                )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")