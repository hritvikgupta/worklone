from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ExtendParserTool(BaseTool):
    name = "extend_parser"
    description = "Parse and extract content from documents using Extend AI"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="extend_api_key",
                description="Extend API key",
                env_var="EXTEND_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "extend",
            context=context,
            context_token_keys=("extend_api_key",),
            env_token_keys=("EXTEND_API_KEY",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "file": {
                    "type": "object",
                    "description": "Document to be processed",
                },
                "outputFormat": {
                    "type": "string",
                    "description": "Target output format (markdown or spatial). Defaults to markdown.",
                },
                "chunking": {
                    "type": "string",
                    "description": "Chunking strategy (page, document, or section). Defaults to page.",
                },
                "engine": {
                    "type": "string",
                    "description": "Parsing engine (parse_performance or parse_light). Defaults to parse_performance.",
                },
            },
            "required": ["file"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        body: Dict[str, Any] = {
            "apiKey": access_token,
        }
        
        file_input = parameters.get("file")
        if not file_input or not isinstance(file_input, dict):
            return ToolResult(
                success=False,
                output="",
                error="Missing or invalid file: Please provide a file object",
            )
        body["file"] = file_input
        
        output_format = parameters.get("outputFormat")
        if output_format and output_format in ["markdown", "spatial"]:
            body["outputFormat"] = output_format
        
        chunking = parameters.get("chunking")
        if chunking and chunking in ["page", "document", "section"]:
            body["chunking"] = chunking
        
        engine = parameters.get("engine")
        if engine and engine in ["parse_performance", "parse_light"]:
            body["engine"] = engine
        
        url = "https://api.extendapi.com/parse"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    try:
                        data = response.json()
                        extend_data = data.get("output", data)
                        output_data = {
                            "id": extend_data.get("id"),
                            "status": extend_data.get("status"),
                            "chunks": extend_data.get("chunks", []),
                            "blocks": extend_data.get("blocks", []),
                            "pageCount": extend_data.get("pageCount") or extend_data.get("page_count"),
                            "creditsUsed": extend_data.get("creditsUsed") or extend_data.get("credits_used"),
                        }
                        return ToolResult(success=True, output=str(output_data), data=output_data)
                    except Exception:
                        return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")