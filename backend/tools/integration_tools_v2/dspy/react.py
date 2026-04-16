from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class DSPyReActTool(BaseTool):
    name = "DSPy ReAct"
    description = "Run a ReAct agent using a self-hosted DSPy ReAct program endpoint for multi-step reasoning and action"
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
                "task": {
                    "type": "string",
                    "description": "The task or question for the ReAct agent to work on",
                },
                "context": {
                    "type": "string",
                    "description": "Additional context to provide for the task",
                },
                "maxIterations": {
                    "type": "number",
                    "description": "Maximum number of reasoning iterations (defaults to server setting)",
                },
            },
            "required": ["baseUrl", "task"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        base_url = parameters.get("baseUrl")
        if not base_url:
            return ToolResult(success=False, output="", error="baseUrl is required.")

        api_key = parameters.get("apiKey")
        endpoint = parameters.get("endpoint", "/predict")
        task = parameters.get("task")
        if not task:
            return ToolResult(success=False, output="", error="task is required.")

        context_str = parameters.get("context")
        max_iters = parameters.get("maxIterations")

        url = base_url.rstrip("/") + endpoint

        headers = {
            "Content-Type": "application/json",
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        body = {
            "text": task,
        }
        if context_str:
            body["context"] = context_str
        if max_iters is not None:
            body["max_iters"] = max_iters

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    status = data.get("status", "success")
                    output_data = data.get("data", data)
                    raw_trajectory = output_data.get("trajectory", {})
                    if isinstance(raw_trajectory, list):
                        trajectory = [
                            {
                                "thought": step.get("thought") or step.get("reasoning") or "",
                                "toolName": step.get("tool_name") or step.get("selected_fn") or "",
                                "toolArgs": step.get("tool_args") or step.get("args") or {},
                                "observation": str(step.get("observation")) if step.get("observation") is not None else None,
                            }
                            for step in raw_trajectory
                        ]
                    else:
                        trajectory = raw_trajectory
                    answer = (
                        output_data.get("answer")
                        or output_data.get("process_result")
                        or output_data.get("output")
                        or output_data.get("response")
                        or ""
                    )
                    transformed = {
                        "answer": answer,
                        "reasoning": output_data.get("reasoning"),
                        "trajectory": trajectory,
                        "status": status,
                        "rawOutput": output_data,
                    }
                    return ToolResult(success=True, output=answer, data=transformed)
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")