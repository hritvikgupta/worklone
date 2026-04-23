from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class ExaAnswerTool(BaseTool):
    name = "exa_answer"
    description = "Get an AI-generated answer to a question with citations from the web using Exa AI."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="EXA_API_KEY",
                description="Exa AI API Key",
                env_var="EXA_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _get_api_key(self, context: dict | None) -> str:
        return (context or {}).get("EXA_API_KEY", "")

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The question to answer",
                },
                "text": {
                    "type": "boolean",
                    "description": "Whether to include the full text of the answer",
                },
            },
            "required": ["query"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = await self._get_api_key(context)

        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Exa AI API key not configured.")

        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
        }

        url = "https://api.exa.ai/answer"

        body = {
            "query": parameters["query"],
        }
        text_param = parameters.get("text")
        if text_param is not None:
            body["text"] = text_param

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")