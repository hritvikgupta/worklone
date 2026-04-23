from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class DatabricksGetRunTool(BaseTool):
    name = "databricks_get_run"
    description = "Get the status, timing, and details of a Databricks job run by its run ID."
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
                "host": {
                    "type": "string",
                    "description": "Databricks workspace host (e.g., dbc-abc123.cloud.databricks.com)",
                },
                "apiKey": {
                    "type": "string",
                    "description": "Databricks Personal Access Token",
                },
                "runId": {
                    "type": "number",
                    "description": "The canonical identifier of the run",
                },
                "includeHistory": {
                    "type": "boolean",
                    "description": "Include repair history in the response",
                },
                "includeResolvedValues": {
                    "type": "boolean",
                    "description": "Include resolved parameter values in the response",
                },
            },
            "required": ["host", "apiKey", "runId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        host = parameters.get("host")
        api_key = parameters.get("apiKey")

        if not host or self._is_placeholder_token(api_key) or self._is_placeholder_token(str(host)):
            return ToolResult(success=False, output="", error="Databricks host or API key not configured.")

        host_clean = host.removeprefix("http://").removeprefix("https://").rstrip("/")

        url = f"https://{host_clean}/api/2.1/jobs/runs/get"

        query_params: Dict[str, Any] = {
            "run_id": parameters["runId"],
        }
        if parameters.get("includeHistory"):
            query_params["include_history"] = "true"
        if parameters.get("includeResolvedValues"):
            query_params["include_resolved_values"] = "true"

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")