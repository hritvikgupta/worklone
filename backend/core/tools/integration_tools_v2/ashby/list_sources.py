from typing import Any, Dict
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class AshbyListSourcesTool(BaseTool):
    name = "ashby_list_sources"
    description = "Lists all candidate sources configured in Ashby."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return []

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "apiKey": {
                    "type": "string",
                    "description": "Ashby API Key",
                },
            },
            "required": ["apiKey"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = parameters.get("apiKey")
        if not api_key or self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Ashby API key not configured.")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {base64.b64encode(f'{api_key}:'.encode('utf-8')).decode('utf-8')}",
        }

        url = "https://api.ashbyhq.com/source.list"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json={})

                if response.status_code in [200, 201, 204]:
                    try:
                        data = response.json()
                        if not data.get("success", False):
                            error_msg = data.get("errorInfo", {}).get("message", "Failed to list sources")
                            return ToolResult(success=False, output="", error=error_msg)
                        return ToolResult(success=True, output=response.text, data=data)
                    except Exception:
                        return ToolResult(success=True, output=response.text, data={})
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")