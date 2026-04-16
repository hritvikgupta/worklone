from typing import Any, Dict
import httpx
import base64
import json
from urllib.parse import quote
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class DocuSignDownloadDocumentTool(BaseTool):
    name = "docusign_download_document"
    description = "Download a signed document from a completed DocuSign envelope"
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
            context_token_keys=("docusign_token",),
            env_token_keys=("DOCUSIGN_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def _get_iss(self, token: str) -> str:
        try:
            parts = token.split(".")
            if len(parts) != 3:
                raise ValueError("Invalid JWT token")
            payload_b64 = parts[1].replace("-", "+").replace("_", "/")
            missing_padding = len(payload_b64) % 4
            if missing_padding:
                payload_b64 += "=" * (4 - missing_padding)
            payload_bytes = base64.b64decode(payload_b64)
            payload = json.loads(payload_bytes.decode("utf-8"))
            iss = payload.get("iss")
            if not iss:
                raise ValueError("No 'iss' claim in token")
            return iss
        except Exception as e:
            raise ValueError(f"Failed to extract issuer from token: {str(e)}")

    async def _get_base_uri(self, access_token: str) -> str:
        iss = self._get_iss(access_token)
        iss_host = iss.rstrip("/")
        tokeninfo_url = f"{iss_host}/oauth/tokeninfo/{quote(access_token)}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(tokeninfo_url)
            if response.status_code != 200:
                raise ValueError(f"Token info failed: {response.status_code} {response.text}")
            tokeninfo = response.json()
            accounts = tokeninfo.get("accounts", [])
            if not accounts:
                raise ValueError("No accounts associated with this token")
            default_account = next((acc for acc in accounts if acc.get("is_default", False)), accounts[0])
            return default_account["base_uri"]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "envelopeId": {
                    "type": "string",
                    "description": "The envelope ID containing the document",
                },
                "documentId": {
                    "type": "string",
                    "description": 'Specific document ID to download, or "combined" for all documents merged (default: "combined")',
                },
            },
            "required": ["envelopeId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        try:
            base_uri = await self._get_base_uri(access_token)
            envelope_id = parameters["envelopeId"]
            document_id = parameters.get("documentId", "combined")
            download_url = f"{base_uri}/envelopes/{envelope_id}/documents/{document_id}"
            headers = {
                "Authorization": f"Bearer {access_token}",
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(download_url, headers=headers)
                
                if response.status_code != 200:
                    return ToolResult(success=False, output="", error=f"Failed to download document: {response.status_code} {response.text}")
                
                content = response.content
                content_b64 = base64.b64encode(content).decode("utf-8")
                mime_type = response.headers.get("content-type", "application/pdf")
                cd = response.headers.get("content-disposition", "")
                file_name = "document.pdf"
                if "filename=" in cd.lower():
                    parts = cd.split("filename=")
                    if len(parts) > 1:
                        file_name = parts[1].split(";")[0].strip().strip('"')
                data = {
                    "base64Content": content_b64,
                    "mimeType": mime_type,
                    "fileName": file_name,
                }
                return ToolResult(success=True, output="Document downloaded successfully.", data=data)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")