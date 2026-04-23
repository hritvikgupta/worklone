from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class DatabricksRunJobTool(BaseTool):
    name = "databricks_run_job"
    description = "Trigger an existing Databricks job to run immediately with optional job-level or notebook parameters."
    category = "integration"

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
                "jobId": {
                    "type": "number",
                    "description": "The ID of the job to trigger",
                },
                "jobParameters": {
                    "type": "string",
                    "description": "Job-level parameter overrides as a JSON object (e.g., {\"key\": \"value\"})",
                },
                "notebookParams": {
                    "type": "string",
                    "description": "Notebook task parameters as a JSON object (e.g., {\"param1\": \"value1\"})",
                },
                "idempotencyToken": {
                    "type": "string",
                    "description": "Idempotency token to prevent duplicate runs (max 64 characters)",
                },
            },
            "required": ["host", "apiKey", "jobId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        try:
            host = parameters["host"]
            api_key = parameters["apiKey"]
            job_id = parameters["jobId"]

            host_clean = host.removeprefix("http://").removeprefix("https://").rstrip("/")
            url = f"https://{host_clean}/api/2.1/jobs/run-now"

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            }

            body: Dict[str, Any] = {
                "job_id": job_id,
            }

            if parameters.get("jobParameters"):
                try:
                    body["job_parameters"] = json.loads(parameters["jobParameters"])
                except json.JSONDecodeError as e:
                    return ToolResult(success=False, output="", error=f"Invalid JSON in jobParameters: {str(e)}")

            if parameters.get("notebookParams"):
                try:
                    body["notebook_params"] = json.loads(parameters["notebookParams"])
                except json.JSONDecodeError as e:
                    return ToolResult(success=False, output="", error=f"Invalid JSON in notebookParams: {str(e)}")

            if parameters.get("idempotencyToken"):
                body["idempotency_token"] = parameters["idempotencyToken"]

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if 200 <= response.status_code < 300:
                    try:
                        data = response.json()
                    except json.JSONDecodeError:
                        data = {}
                    structured_data = {
                        "runId": data.get("run_id", 0),
                        "numberInJob": data.get("number_in_job", 0),
                    }
                    return ToolResult(success=True, output=response.text, data=structured_data)
                else:
                    error_msg = response.text
                    try:
                        err_data = response.json()
                        if "message" in err_data:
                            error_msg = err_data["message"]
                        elif "error" in err_data:
                            error = err_data["error"]
                            if isinstance(error, dict) and "message" in error:
                                error_msg = error["message"]
                            else:
                                error_msg = str(error)
                    except (json.JSONDecodeError, KeyError, TypeError):
                        pass
                    return ToolResult(
                        success=False, output="", error=error_msg or "Failed to trigger job run"
                    )
        except httpx.RequestError as e:
            return ToolResult(success=False, output="", error=f"Request failed: {str(e)}")
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")