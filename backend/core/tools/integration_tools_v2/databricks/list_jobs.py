from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class DatabricksListJobsTool(BaseTool):
    name = "databricks_list_jobs"
    description = "List all jobs in a Databricks workspace with optional filtering by name."
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
                key="DATABRICKS_API_KEY",
                description="Databricks Personal Access Token",
                env_var="DATABRICKS_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_host(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "databricks",
            context=context,
            context_token_keys=("databricks_host",),
            env_token_keys=("DATABRICKS_HOST",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        host = connection.access_token
        normalized = host.replace("http://", "").replace("https://", "").rstrip("/")
        return normalized

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "databricks",
            context=context,
            context_token_keys=("databricks_api_key",),
            env_token_keys=("DATABRICKS_API_KEY",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "number",
                    "description": "Maximum number of jobs to return (range 1-100, default 20)",
                },
                "offset": {
                    "type": "number",
                    "description": "Offset for pagination",
                },
                "name": {
                    "type": "string",
                    "description": "Filter jobs by exact name (case-insensitive)",
                },
                "expandTasks": {
                    "type": "boolean",
                    "description": "Include task and cluster details in the response (max 100 elements)",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        try:
            host = await self._resolve_host(context)
            access_token = await self._resolve_access_token(context)
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Credential resolution error: {str(e)}")

        if self._is_placeholder_token(access_token) or self._is_placeholder_token(host):
            return ToolResult(success=False, output="", error="Databricks host or access token not configured.")

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        }

        url = f"https://{host}/api/2.1/jobs/list"

        params = {}
        limit = parameters.get("limit")
        if limit is not None:
            params["limit"] = limit
        offset = parameters.get("offset")
        if offset is not None:
            params["offset"] = offset
        name = parameters.get("name")
        if name:
            params["name"] = name
        expand_tasks = parameters.get("expandTasks")
        if expand_tasks:
            params["expand_tasks"] = "true"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params)

                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    jobs = []
                    jobs_raw = data.get("jobs", [])
                    for job in jobs_raw:
                        settings = job.get("settings", {})
                        jobs.append({
                            "jobId": job.get("job_id", 0),
                            "name": settings.get("name", ""),
                            "createdTime": job.get("created_time", 0),
                            "creatorUserName": job.get("creator_user_name", ""),
                            "maxConcurrentRuns": settings.get("max_concurrent_runs", 1),
                            "format": settings.get("format", ""),
                        })
                    result = {
                        "jobs": jobs,
                        "hasMore": data.get("has_more", False),
                        "nextPageToken": data.get("next_page_token"),
                    }
                    output_str = json.dumps(result)
                    return ToolResult(success=True, output=output_str, data=result)
                else:
                    data = response.json()
                    error_msg = (
                        data.get("message")
                        or data.get("error", {}).get("message")
                        or response.text
                        or "Failed to list jobs"
                    )
                    return ToolResult(success=False, output="", error=error_msg)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")