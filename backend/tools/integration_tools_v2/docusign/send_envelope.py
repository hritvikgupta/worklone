from typing import Any, Dict
import httpx
import base64
import json
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class DocuSignSendEnvelopeTool(BaseTool):
    name = "docusign_send_envelope"
    description = "Create and send a DocuSign envelope with a document for e-signature"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    @staticmethod
    def _get_iss_from_token(token: str) -> str:
        try:
            parts = token.split(".")
            if len(parts) != 3:
                raise ValueError("Invalid JWT token format")
            payload_b64 = parts[1]
            payload_b64 += "=" * ((4 - len(payload_b64) % 4) % 4)
            payload_bytes = base64.urlsafe_b64decode(payload_b64)
            payload = json.loads(payload_bytes.decode("utf-8"))
            return payload["iss"]
        except Exception:
            raise ValueError("Failed to extract issuer from access token")

    async def _get_docusign_info(self, access_token: str) -> tuple[str, str]:
        iss = self._get_iss_from_token(access_token)
        userinfo_url = f"{iss.rstrip('/')}/oauth/userinfo"
        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(userinfo_url, headers=headers)
            response.raise_for_status()
            data = response.json()
            accounts = data.get("accounts", [])
            if not accounts:
                raise ValueError("No DocuSign accounts found for this access token")
            account = accounts[0]
            base_uri = account["base_uri"].rstrip("/")
            account_id = account["account_id"]
            return base_uri, account_id

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
                "emailSubject": {
                    "type": "string",
                    "description": "Email subject for the envelope",
                },
                "emailBody": {
                    "type": "string",
                    "description": "Email body message",
                },
                "signerEmail": {
                    "type": "string",
                    "description": "Email address of the signer",
                },
                "signerName": {
                    "type": "string",
                    "description": "Full name of the signer",
                },
                "ccEmail": {
                    "type": "string",
                    "description": "Email address of carbon copy recipient",
                },
                "ccName": {
                    "type": "string",
                    "description": "Full name of carbon copy recipient",
                },
                "file": {
                    "type": "string",
                    "description": "Base64-encoded document file to send for signature",
                },
                "status": {
                    "type": "string",
                    "description": 'Envelope status: "sent" to send immediately, "created" for draft (default: "sent")',
                },
            },
            "required": ["emailSubject", "signerEmail", "signerName"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        try:
            base_uri, account_id = await self._get_docusign_info(access_token)
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Failed to retrieve DocuSign account: {str(e)}")

        file_data = parameters.get("file")
        if not file_data:
            return ToolResult(
                success=False, output="", error="Document file is required to create the envelope."
            )

        try:
            document_bytes = base64.b64decode(file_data)
        except Exception as e:
            return ToolResult(
                success=False, output="", error=f"Invalid base64-encoded file: {str(e)}"
            )

        ext = "pdf"
        if document_bytes.startswith(b"%PDF-"):
            ext = "pdf"
        elif document_bytes.startswith(b"PK\x03\x04"):
            ext = "docx"
        elif document_bytes.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
            ext = "doc"

        documents = [
            {
                "documentBase64": base64.b64encode(document_bytes).decode("ascii"),
                "name": f"Document.{ext}",
                "fileExtension": ext,
                "documentId": "1",
            }
        ]

        signers = [
            {
                "email": parameters["signerEmail"],
                "name": parameters["signerName"],
                "recipientId": "1",
                "routingOrder": "1",
                "tabs": {
                    "signHereTabs": [
                        {
                            "documentId": "1",
                            "pageNumber": "1",
                            "xPosition": 400,
                            "yPosition": 600,
                            "width": 200,
                            "height": 50,
                        }
                    ]
                },
            }
        ]

        ccs: list[dict] = []
        cc_email = parameters.get("ccEmail")
        cc_name = parameters.get("ccName")
        if cc_email and cc_name:
            ccs = [
                {
                    "email": cc_email,
                    "name": cc_name,
                    "recipientId": "2",
                    "routingOrder": "1",
                }
            ]

        recipients = {"signers": signers}
        if ccs:
            recipients["ccs"] = ccs

        envelope_definition = {
            "status": parameters.get("status", "sent"),
            "emailSubject": parameters["emailSubject"],
            "emailBlurb": parameters.get("emailBody", ""),
            "documents": documents,
            "recipients": recipients,
        }

        url = f"{base_uri}/restapi/v2.1/accounts/{account_id}/envelopes"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=envelope_definition)

                if response.status_code in [200, 201]:
                    return ToolResult(
                        success=True, output=response.text, data=response.json()
                    )
                else:
                    error_msg = response.text
                    try:
                        err_data = response.json()
                        error_msg = (
                            err_data.get("errorMessage")
                            or err_data.get("message", error_msg)
                            or error_msg
                        )
                    except ValueError:
                        pass
                    return ToolResult(
                        success=False, output="", error=f"DocuSign API error ({response.status_code}): {error_msg}"
                    )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")