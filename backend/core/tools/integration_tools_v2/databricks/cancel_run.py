from typing import Any, Dict
import httpx
import re
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class DatabricksCancelRunTool(BaseTool):
    name = "databricks_cancel_run"
    description = "Cancel a running or pending Databricks job run. Cancellation is asynchronous; poll the run status to confirm termination."
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
                "runId": {
                    "type": "number",
                    "description": "The canonical identifier of the run to cancel",
                },
            },
            "required": ["runId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        try:
            host = parameters["host"]
            api_key = parameters["apiKey"]
            run_id = parameters["runId"]
        except KeyError as e:
            return ToolResult(success=False, output="", error=f"Missing required parameter: {str(e).split('\'')[1]}")

        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Databricks API key not configured.")

        if self._is_placeholder_token(host):
            return ToolResult(success=False, output="", error="Databricks host not configured.")

        host = re.sub(r'^https?://', '', host).rstrip('/')
        url = f"https://{host}/api/2.1/jobs/runs/cancel"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        body = {
            "run_id": run_id,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    try:
                        data = response.json()
                        message = data.get("message")
                        if not message and "error" in data:
                            error_obj = data["error"]
                            if isinstance(error_obj, dict):
                                message = error_obj.get("message")
                        if not message:
                            message = response.text
                    except Exception:
                        message = response.text
                    return ToolResult(success=False, output="", error=message)
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")