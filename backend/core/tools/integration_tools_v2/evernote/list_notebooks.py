from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class EvernoteListNotebooksTool(BaseTool):
    name = "evernote_list_notebooks"
    description = "List all notebooks in an Evernote account"
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
                    "description": "Evernote developer token"
                }
            },
            "required": ["apiKey"]
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = parameters.get("apiKey")

        if not api_key:
            return ToolResult(success=False, output="", error="apiKey is required")

        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        url = "https://sandbox.evernote.com/api/notebooks"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json={})

                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    notebooks = data.get("notebooks", data.get("data", [])) if isinstance(data, dict) else data
                    return ToolResult(
                        success=True,
                        output=response.text,
                        data={"notebooks": notebooks}
                    )
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")