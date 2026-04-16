from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class LangsmithCreateRunTool(BaseTool):
    name = "LangSmith Create Run"
    description = "Forward a single run to LangSmith for ingestion."
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
                    "description": "LangSmith API key",
                },
                "id": {
                    "type": "string",
                    "description": "Unique run identifier",
                },
                "name": {
                    "type": "string",
                    "description": "Run name",
                },
                "run_type": {
                    "type": "string",
                    "description": "Run type (tool, chain, llm, retriever, embedding, prompt, parser)",
                },
                "start_time": {
                    "type": "string",
                    "description": "Run start time in ISO-8601 format",
                },
                "end_time": {
                    "type": "string",
                    "description": "Run end time in ISO-8601 format",
                },
                "inputs": {
                    "type": "object",
                    "description": "Inputs payload",
                },
                "run_outputs": {
                    "type": "object",
                    "description": "Outputs payload",
                },
                "extra": {
                    "type": "object",
                    "description": "Additional metadata (extra)",
                },
                "tags": {
                    "type": "array",
                    "items": {
                        "type": "string",
                    },
                    "description": "Array of tag strings",
                },
                "parent_run_id": {
                    "type": "string",
                    "description": "Parent run ID",
                },
                "trace_id": {
                    "type": "string",
                    "description": "Trace ID",
                },
                "session_id": {
                    "type": "string",
                    "description": "Session ID",
                },
                "session_name": {
                    "type": "string",
                    "description": "Session name",
                },
                "status": {
                    "type": "string",
                    "description": "Run status",
                },
                "error": {
                    "type": "string",
                    "description": "Error details",
                },
                "dotted_order": {
                    "type": "string",
                    "description": "Dotted order string",
                },
                "events": {
                    "type": "array",
                    "items": {
                        "type": "object",
                    },
                    "description": "Structured events array",
                },
            },
            "required": ["apiKey", "name", "run_type"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = parameters.get("apiKey")
        if self._is_placeholder_token(api_key or ""):
            return ToolResult(success=False, output="", error="LangSmith API key not configured.")

        headers = {
            "X-Api-Key": api_key,
            "Content-Type": "application/json",
        }

        payload = {
            "id": parameters.get("id"),
            "name": (parameters.get("name") or "").strip(),
            "run_type": parameters.get("run_type"),
            "start_time": parameters.get("start_time"),
            "end_time": parameters.get("end_time"),
            "inputs": parameters.get("inputs"),
            "outputs": parameters.get("run_outputs"),
            "extra": parameters.get("extra"),
            "tags": parameters.get("tags"),
            "parent_run_id": parameters.get("parent_run_id"),
            "trace_id": parameters.get("trace_id"),
            "session_id": parameters.get("session_id"),
            "session_name": parameters.get("session_name"),
            "status": parameters.get("status"),
            "error": parameters.get("error"),
            "dotted_order": parameters.get("dotted_order"),
            "events": parameters.get("events"),
        }
        body = {k: v for k, v in payload.items() if v is not None}

        url = "https://api.smith.langchain.com/runs"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    try:
                        data = response.json()
                        run_id = parameters.get("id")
                        message = None
                        if isinstance(data.get("message"), str):
                            message = data["message"]
                        elif run_id and run_id in data and isinstance(data[run_id], dict):
                            nested_payload = data[run_id]
                            if isinstance(nested_payload.get("message"), str):
                                message = nested_payload["message"]
                        parsed = {
                            "accepted": True,
                            "runId": run_id,
                            "message": message,
                        }
                        return ToolResult(success=True, output=str(parsed), data=parsed)
                    except:
                        return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")