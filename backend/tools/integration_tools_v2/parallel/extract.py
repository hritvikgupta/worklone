import os
from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class ParallelExtractTool(BaseTool):
    name = "parallel_extract"
    description = "Extract targeted information from specific URLs using Parallel AI. Processes provided URLs to pull relevant content based on your objective."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="PARALLEL_API_KEY",
                description="Parallel AI API Key",
                env_var="PARALLEL_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_api_key(self, context: dict | None) -> str:
        api_key = context.get("provider_token") if context else None
        if self._is_placeholder_token(api_key or ""):
            api_key = os.environ.get("PARALLEL_API_KEY", "")
        return api_key or ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "urls": {
                    "type": "string",
                    "description": "Comma-separated list of URLs to extract information from",
                },
                "objective": {
                    "type": "string",
                    "description": "What information to extract from the provided URLs",
                },
                "excerpts": {
                    "type": "boolean",
                    "description": "Include relevant excerpts from the content (default: true)",
                },
                "full_content": {
                    "type": "boolean",
                    "description": "Include full page content as markdown (default: false)",
                },
            },
            "required": ["urls"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = await self._resolve_api_key(context)
        
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Parallel API key not configured.")
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "parallel-beta": "search-extract-2025-10-10",
        }
        
        urls_str = parameters["urls"]
        url_array = [url.strip() for url in urls_str.split(",") if len(url.strip()) > 0]
        body = {
            "urls": url_array,
        }
        objective = parameters.get("objective")
        if objective:
            body["objective"] = objective
        if "excerpts" in parameters:
            body["excerpts"] = parameters["excerpts"]
        if "full_content" in parameters:
            body["full_content"] = parameters["full_content"]
        
        url = "https://api.parallel.ai/v1beta/extract"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")