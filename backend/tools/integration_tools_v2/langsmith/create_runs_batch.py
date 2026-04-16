from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class LangsmithCreateRunsBatchTool(BaseTool):
    name = "langsmith_create_runs_batch"
    description = "Forward multiple runs to LangSmith in a single batch."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="langsmith_api_key",
                description="LangSmith API key",
                env_var="LANGsmith_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def _get_api_key(self, context: dict | None) -> str:
        if not context:
            return ""
        api_key = context.get("langsmith_api_key")
        return api_key or ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "post": {
                    "type": "array",
                    "description": "Array of new runs to ingest",
                    "items": {
                        "type": "object"
                    }
                },
                "patch": {
                    "type": "array",
                    "description": "Array of runs to update/patch",
                    "items": {
                        "type": "object"
                    }
                }
            },
            "required": []
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = self._get_api_key(context)
        
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="LangSmith API key not configured.")
        
        headers = {
            "X-Api-Key": api_key,
            "Content-Type": "application/json",
        }
        
        url = "https://api.smith.langchain.com/runs/batch"
        
        payload: Dict[str, Any] = {}
        if parameters.get("post") is not None:
            payload["post"] = parameters["post"]
        if parameters.get("patch") is not None:
            payload["patch"] = parameters["patch"]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")