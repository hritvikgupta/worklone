from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleDocsWriteTool(BaseTool):
    name = "google_docs_write"
    description = "Write or update content in a Google Docs document"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GOOGLE_DOCS_ACCESS_TOKEN",
                description="Access token",
                env_var="GOOGLE_DOCS_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "google-docs",
            context=context,
            context_token_keys=("provider_token",),
            env_token_keys=("GOOGLE_DOCS_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "documentId": {
                    "type": "string",
                    "description": "The ID of the document to write to",
                },
                "content": {
                    "type": "string",
                    "description": "The content to write to the document",
                },
            },
            "required": ["documentId", "content"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        document_id = (parameters.get("documentId") or "").strip()
        if not document_id:
            return ToolResult(success=False, output="", error="Document ID is required")
        
        content = parameters.get("content") or ""
        if not content:
            return ToolResult(success=False, output="", error="Content is required")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = f"https://docs.googleapis.com/v1/documents/{document_id}:batchUpdate"
        
        body = {
            "requests": [
                {
                    "insertText": {
                        "endOfSegmentLocation": {},
                        "text": content,
                    },
                },
            ],
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    metadata = {
                        "documentId": document_id,
                        "title": "Updated Document",
                        "mimeType": "application/vnd.google-apps.document",
                        "url": f"https://docs.google.com/document/d/{document_id}/edit",
                    }
                    result_data = {
                        "updatedContent": True,
                        "metadata": metadata,
                    }
                    return ToolResult(
                        success=True,
                        output=json.dumps(result_data),
                        data=result_data,
                    )
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")