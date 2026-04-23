from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleDocsReadTool(BaseTool):
    name = "google_docs_read"
    description = "Read content from a Google Docs document"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GOOGLE_DOCS_ACCESS_TOKEN",
                description="Access token for the Google Docs API",
                env_var="GOOGLE_DOCS_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "google-docs",
            context=context,
            context_token_keys=("accessToken",),
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
                    "description": "Google Docs document ID",
                }
            },
            "required": ["documentId"],
        }

    def _extract_text_from_document(self, document: Dict[str, Any]) -> str:
        def extract_text(element: Dict[str, Any]) -> str:
            text_parts = []
            if "paragraphElement" in element:
                elements = element["paragraphElement"].get("elements", [])
                for el in elements:
                    if "textRun" in el and "content" in el["textRun"]:
                        text_parts.append(el["textRun"]["content"])
            elif "tableElement" in element:
                table_rows = element["tableElement"].get("tableRows", [])
                for row in table_rows:
                    table_cells = row.get("tableCells", [])
                    for cell in table_cells:
                        cell_content = cell.get("content", [])
                        for cell_el in cell_content:
                            text_parts.append(extract_text(cell_el))
            return "".join(text_parts)

        body_content = document.get("body", {}).get("content", [])
        all_text = []
        for element in body_content:
            all_text.append(extract_text(element))
        return "".join(all_text)

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        document_id = parameters.get("documentId", "").strip()
        if not document_id:
            return ToolResult(success=False, output="", error="Document ID is required.")

        url = f"https://docs.googleapis.com/v1/documents/{document_id}"
        headers = {
            "Authorization": f"Bearer {access_token}",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    content = self._extract_text_from_document(data)
                    metadata = {
                        "documentId": data.get("documentId"),
                        "title": data.get("title", "Untitled Document"),
                        "mimeType": "application/vnd.google-apps.document",
                        "url": f"https://docs.google.com/document/d/{data.get('documentId')}/edit",
                    }
                    result_data = {
                        "content": content,
                        "metadata": metadata,
                    }
                    return ToolResult(success=True, output=content, data=result_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")