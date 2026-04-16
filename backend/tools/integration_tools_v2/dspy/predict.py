from typing import Any, Dict
import httpx
import json
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class DSPyPredictTool(BaseTool):
    name = "dspy_predict"
    description = "Run a prediction using a self-hosted DSPy program endpoint"
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
                "input": {
                    "type": "string",
                    "description": "The input text to send to the DSPy program",
                },
                "inputField": {
                    "type": "string",
                    "description": 'Name of the input field expected by the DSPy program (defaults to "text")',
                },
                "context": {
                    "type": "string",
                    "description": "Additional context to provide to the DSPy program",
                },
                "additionalInputs": {
                    "type": "object",
                    "description": "Additional key-value pairs to include in the request body",
                },
            },
            "required": ["baseUrl", "input"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        base_url = parameters["baseUrl"].rstrip("/")
        endpoint = parameters.get("endpoint") or "/predict"
        url = f"{base_url}{endpoint}"

        headers: Dict[str, str] = {
            "Content-Type": "application/json",
        }
        api_key = parameters.get("apiKey")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        input_field = parameters.get("inputField", "text")
        body: Dict[str, Any] = {
            input_field: parameters["input"],
        }
        ctx = parameters.get("context")
        if ctx:
            body["context"] = ctx
        additional = parameters.get("additionalInputs")
        if additional:
            body.update(additional)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    try:
                        data = response.json()
                    except Exception:
                        return ToolResult(success=False, output=response.text, error="Invalid JSON response")

                    status = data.get("status", "success")
                    output_data = data.get("data", data)
                    answer = (
                        output_data.get("answer")
                        or output_data.get("output")
                        or output_data.get("response")
                        or ""
                    )
                    reasoning = output_data.get("reasoning") or output_data.get("rationale")
                    transformed_output = {
                        "answer": answer,
                        "reasoning": reasoning,
                        "status": status,
                        "rawOutput": output_data,
                    }
                    return ToolResult(
                        success=True,
                        output=json.dumps(transformed_output),
                        data=transformed_output,
                    )
                else:
                    return ToolResult(success=False, output="", error=response.text)
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")