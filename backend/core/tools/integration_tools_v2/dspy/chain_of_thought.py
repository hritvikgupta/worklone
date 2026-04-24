from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class DSPyChainOfThoughtTool(BaseTool):
    name = "dspy_chain_of_thought"
    description = "Run a Chain of Thought prediction using a self-hosted DSPy ChainOfThought program endpoint"
    category = "integration"

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return []

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "baseUrl": {
                    "type": "string",
                    "description": "Base URL of the DSPy server (e.g., https://your-dspy-server.com)",
                },
                "apiKey": {
                    "type": "string",
                    "description": "API key for authentication (if required by your server)",
                },
                "endpoint": {
                    "type": "string",
                    "description": "API endpoint path (defaults to /predict)",
                },
                "question": {
                    "type": "string",
                    "description": "The question to answer using chain of thought reasoning",
                },
                "context": {
                    "type": "string",
                    "description": "Additional context to provide for answering the question",
                },
            },
            "required": ["baseUrl", "question"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        base_url = parameters["baseUrl"].rstrip("/")
        endpoint = parameters.get("endpoint", "/predict")
        url = f"{base_url}{endpoint}"

        headers = {
            "Content-Type": "application/json",
        }
        api_key = parameters.get("apiKey")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        body = {
            "text": parameters["question"],
        }
        ctx = parameters.get("context")
        if ctx:
            body["context"] = ctx

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")