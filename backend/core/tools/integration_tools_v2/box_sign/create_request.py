from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class BoxSignCreateRequestTool(BaseTool):
    name = "box_sign_create_request"
    description = "Create a new Box Sign request to send documents for e-signature"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="BOX_ACCESS_TOKEN",
                description="OAuth access token for Box API",
                env_var="BOX_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection("box_sign",
            context=context,
            context_token_keys=("provider_token",),
            env_token_keys=("BOX_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "sourceFileIds": {
                    "type": "string",
                    "description": "Comma-separated Box file IDs to send for signing",
                },
                "signerEmail": {
                    "type": "string",
                    "description": "Primary signer email address",
                },
                "signerRole": {
                    "type": "string",
                    "description": "Primary signer role: signer, approver, or final_copy_reader (default: signer)",
                },
                "additionalSigners": {
                    "type": "string",
                    "description": 'JSON array of additional signers, e.g. [{"email":"user@example.com","role":"signer"}]',
                },
                "parentFolderId": {
                    "type": "string",
                    "description": "Box folder ID where signed documents will be stored (default: user root)",
                },
                "emailSubject": {
                    "type": "string",
                    "description": "Custom subject line for the signing email",
                },
                "emailMessage": {
                    "type": "string",
                    "description": "Custom message in the signing email body",
                },
                "name": {
                    "type": "string",
                    "description": "Name for the sign request",
                },
                "daysValid": {
                    "type": "number",
                    "description": "Number of days before the request expires (0-730)",
                },
                "areRemindersEnabled": {
                    "type": "boolean",
                    "description": "Whether to send automatic signing reminders",
                },
                "areTextSignaturesEnabled": {
                    "type": "boolean",
                    "description": "Whether to allow typed (text) signatures",
                },
                "signatureColor": {
                    "type": "string",
                    "description": "Signature color: blue, black, or red",
                },
                "redirectUrl": {
                    "type": "string",
                    "description": "URL to redirect signers to after signing",
                },
                "declinedRedirectUrl": {
                    "type": "string",
                    "description": "URL to redirect signers to after declining",
                },
                "isDocumentPreparationNeeded": {
                    "type": "boolean",
                    "description": "Whether document preparation is needed before sending",
                },
                "externalId": {
                    "type": "string",
                    "description": "External system reference ID",
                },
            },
            "required": ["sourceFileIds", "signerEmail"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = "https://api.box.com/2.0/sign_requests"
        
        source_file_ids_str = parameters.get("sourceFileIds", "")
        file_ids = [fid.strip() for fid in source_file_ids_str.split(",") if fid.strip()]
        source_files = [{"type": "file", "id": fid} for fid in file_ids]
        
        signers = [
            {
                "email": parameters["signerEmail"],
                "role": parameters.get("signerRole") or "signer",
            }
        ]
        
        additional_signers_str = parameters.get("additionalSigners")
        if additional_signers_str:
            try:
                add_signers = json.loads(additional_signers_str)
                if not isinstance(add_signers, list):
                    return ToolResult(
                        success=False,
                        output="",
                        error="Invalid JSON in additionalSigners. Expected a JSON array of signer objects.",
                    )
                signers.extend(add_signers)
            except json.JSONDecodeError:
                return ToolResult(
                    success=False,
                    output="",
                    error="Invalid JSON in additionalSigners. Expected a JSON array of signer objects.",
                )
        
        body: dict = {
            "source_files": source_files,
            "signers": signers,
        }
        
        p = parameters.get("parentFolderId")
        if p is not None:
            body["parent_folder"] = {"type": "folder", "id": p}
        p = parameters.get("emailSubject")
        if p is not None:
            body["email_subject"] = p
        p = parameters.get("emailMessage")
        if p is not None:
            body["email_message"] = p
        p = parameters.get("name")
        if p is not None:
            body["name"] = p
        p = parameters.get("daysValid")
        if p is not None:
            body["days_valid"] = p
        p = parameters.get("areRemindersEnabled")
        if p is not None:
            body["are_reminders_enabled"] = p
        p = parameters.get("areTextSignaturesEnabled")
        if p is not None:
            body["are_text_signatures_enabled"] = p
        p = parameters.get("signatureColor")
        if p is not None:
            body["signature_color"] = p
        p = parameters.get("redirectUrl")
        if p is not None:
            body["redirect_url"] = p
        p = parameters.get("declinedRedirectUrl")
        if p is not None:
            body["declined_redirect_url"] = p
        p = parameters.get("isDocumentPreparationNeeded")
        if p is not None:
            body["is_document_preparation_needed"] = p
        p = parameters.get("externalId")
        if p is not None:
            body["external_id"] = p
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")