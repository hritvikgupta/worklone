from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class DatabricksGetRunOutputTool(BaseTool):
    name = "databricks_get_run_output"
    description = "Get the output of a completed Databricks job run, including notebook results, error messages, and logs. For multi-task jobs, use the task run ID (not the parent run ID)."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="DATABRICKS_HOST",
                description="Databricks workspace host (e.g., dbc-abc123.cloud.databricks.com)",
                env_var="DATABRICKS_HOST",
                required=True,
                auth_type="api_key",
            ),
            CredentialRequirement(
                key="DATABRICKS_ACCESS_TOKEN",
                description="Databricks Personal Access Token",
                env_var="DATABRICKS_ACCESS_TOKEN",
                required=True,
                auth_type="api_key",
            ),
        ]

    def _resolve_host(self, context: dict | None) -> str:
        host = context.get("databricks_host") if context else ""
        return host or ""

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "databricks",
            context=context,
            context_token_keys=("databricks_token",),
            env_token_keys=("DATABRICKS_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "runId": {
                    "type": "number",
                    "description": "The run ID to get output for. For multi-task jobs, use the task run ID",
                },
            },
            "required": ["runId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        host = self._resolve_host(context)
        if self._is_placeholder_token(host):
            return ToolResult(success=False, output="", error="Databricks host not configured.")

        access_token = await self._resolve_access_token(context)
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        run_id = parameters.get("runId")
        if not run_id:
            return ToolResult(success=False, output="", error="runId is required.")

        try:
            run_id_int = int(float(run_id))
        except (ValueError, TypeError):
            return ToolResult(success=False, output="", error="runId must be a valid number.")

        host_clean = host.replace("http://", "").replace("https://", "").rstrip("/")
        url = f"https://{host_clean}/api/2.1/jobs/runs/get-output?run_id={run_id_int}"

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code != 200:
                    try:
                        error_data = response.json()
                    except:
                        error_data = {}
                    error_msg = (
                        error_data.get("message")
                        or error_data.get("error", {}).get("message")
                        or response.text
                        or "Failed to get run output"
                    )
                    return ToolResult(success=False, output="", error=error_msg)

                data = response.json()

                notebook_output = data.get("notebook_output")
                notebookOutput = None
                if notebook_output:
                    notebookOutput = {
                        "result": notebook_output.get("result"),
                        "truncated": notebook_output.get("truncated", False),
                    }

                output_data = {
                    "notebookOutput": notebookOutput,
                    "error": data.get("error"),
                    "errorTrace": data.get("error_trace"),
                    "logs": data.get("logs"),
                    "logsTruncated": data.get("logs_truncated", False),
                }

                return ToolResult(success=True, output=response.text, data=output_data)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")