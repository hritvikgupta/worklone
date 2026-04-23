from typing import Any, Dict
import httpx
import os
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class ReductoParserTool(BaseTool):
    name = "reducto_parser"
    description = "Parse PDF documents using Reducto OCR API"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="REDUCTO_API_KEY",
                description="Reducto API key (REDUCTO_API_KEY)",
                env_var="REDUCTO_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        token = None
        if context:
            token = context.get("REDUCTO_API_KEY")
        if token is None:
            token = os.getenv("REDUCTO_API_KEY", "")
        return token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "file": {
                    "type": "string",
                    "description": "PDF document to be processed",
                },
                "pages": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Specific pages to process (1-indexed page numbers)",
                },
                "tableOutputFormat": {
                    "type": "string",
                    "description": "Table output format (html or markdown). Defaults to markdown.",
                },
            },
            "required": ["file"],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        file_input = parameters.get("file")
        if not file_input:
            return ToolResult(success=False, output="", error="Missing or invalid file: Please provide a PDF document")
        
        body: Dict[str, Any] = {
            "apiKey": access_token,
            "file": file_input,
        }
        
        table_output_format = parameters.get("tableOutputFormat")
        if isinstance(table_output_format, str) and table_output_format in ["html", "md"]:
            body["tableOutputFormat"] = table_output_format
        
        pages = parameters.get("pages")
        if pages is not None:
            if isinstance(pages, list) and len(pages) > 0:
                valid_pages = [
                    int(page)
                    for page in pages
                    if isinstance(page, (int, float)) and float(page).is_integer() and int(page) >= 0
                ]
                if valid_pages:
                    body["pages"] = valid_pages
        
        url = "https://api.reducto.ai/v1/parse"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    reducto_data = data.get("output") if isinstance(data, dict) else data
                    output_data = {
                        "job_id": reducto_data.get("job_id") if isinstance(reducto_data, dict) else None,
                        "duration": reducto_data.get("duration") if isinstance(reducto_data, dict) else None,
                        "usage": reducto_data.get("usage") if isinstance(reducto_data, dict) else None,
                        "result": reducto_data.get("result") if isinstance(reducto_data, dict) else None,
                        "pdf_url": reducto_data.get("pdf_url") if isinstance(reducto_data, dict) else None,
                        "studio_link": reducto_data.get("studio_link") if isinstance(reducto_data, dict) else None,
                    }
                    return ToolResult(success=True, output=str(output_data), data=output_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")