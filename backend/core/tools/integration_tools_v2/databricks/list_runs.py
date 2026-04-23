from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class DatabricksListRunsTool(BaseTool):
    name = "databricks_list_runs"
    description = "List job runs in a Databricks workspace with optional filtering by job, status, and time range."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="DATABRICKS_API_KEY",
                description="Databricks Personal Access Token",
                env_var="DATABRICKS_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "databricks",
            context=context,
            context_token_keys=("provider_token",),
            env_token_keys=("DATABRICKS_API_KEY",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "host": {
                    "type": "string",
                    "description": "Databricks workspace host (e.g., dbc-abc123.cloud.databricks.com)",
                },
                "jobId": {
                    "type": "number",
                    "description": "Filter runs by job ID. Omit to list runs across all jobs",
                },
                "activeOnly": {
                    "type": "boolean",
                    "description": "Only include active runs (PENDING, RUNNING, or TERMINATING)",
                },
                "completedOnly": {
                    "type": "boolean",
                    "description": "Only include completed runs",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of runs to return (range 1-24, default 20)",
                },
                "offset": {
                    "type": "number",
                    "description": "Offset for pagination",
                },
                "runType": {
                    "type": "string",
                    "description": "Filter by run type (JOB_RUN, WORKFLOW_RUN, SUBMIT_RUN)",
                },
                "startTimeFrom": {
                    "type": "number",
                    "description": "Filter runs started at or after this timestamp (epoch ms)",
                },
                "startTimeTo": {
                    "type": "number",
                    "description": "Filter runs started at or before this timestamp (epoch ms)",
                },
            },
            "required": ["host"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        host = (parameters.get("host") or "").strip()
        host = host.replace("http://", "").replace("https://", "").rstrip("/")
        if not host:
            return ToolResult(success=False, output="", error="Databricks host is required.")
        
        url = f"https://{host}/api/2.1/jobs/runs/list"
        
        params_dict: Dict[str, str] = {}
        if "jobId" in parameters:
            job_id = parameters["jobId"]
            if job_id is not None:
                params_dict["job_id"] = str(job_id)
        if "activeOnly" in parameters and parameters["activeOnly"]:
            params_dict["active_only"] = "true"
        if "completedOnly" in parameters and parameters["completedOnly"]:
            params_dict["completed_only"] = "true"
        if "limit" in parameters:
            limit = parameters["limit"]
            if limit is not None:
                params_dict["limit"] = str(limit)
        if "offset" in parameters:
            offset = parameters["offset"]
            if offset is not None:
                params_dict["offset"] = str(offset)
        if "runType" in parameters and parameters["runType"]:
            params_dict["run_type"] = parameters["runType"]
        if "startTimeFrom" in parameters:
            start_time_from = parameters["startTimeFrom"]
            if start_time_from is not None:
                params_dict["start_time_from"] = str(start_time_from)
        if "startTimeTo" in parameters:
            start_time_to = parameters["startTimeTo"]
            if start_time_to is not None:
                params_dict["start_time_to"] = str(start_time_to)
        
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params_dict)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")