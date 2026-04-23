from typing import Any, Dict
import httpx
import json
import urllib.parse
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleBigQueryListDatasetsTool(BaseTool):
    name = "BigQuery List Datasets"
    description = "List all datasets in a Google BigQuery project"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GOOGLE_BIGQUERY_ACCESS_TOKEN",
                description="OAuth access token for Google BigQuery",
                env_var="GOOGLE_BIGQUERY_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "google",
            context=context,
            context_token_keys=("access_token",),
            env_token_keys=("GOOGLE_BIGQUERY_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "projectId": {
                    "type": "string",
                    "description": "Google Cloud project ID",
                },
                "maxResults": {
                    "type": "number",
                    "description": "Maximum number of datasets to return",
                },
                "pageToken": {
                    "type": "string",
                    "description": "Token for pagination",
                },
            },
            "required": ["projectId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        
        project_id = parameters["projectId"]
        base_url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{urllib.parse.quote(project_id)}/datasets"
        
        params: Dict[str, Any] = {}
        if "maxResults" in parameters:
            max_results = parameters["maxResults"]
            if max_results is not None:
                try:
                    max_results = int(max_results)
                    if max_results > 0:
                        params["maxResults"] = max_results
                except (ValueError, TypeError):
                    pass
        if "pageToken" in parameters and parameters["pageToken"]:
            params["pageToken"] = parameters["pageToken"]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(base_url, headers=headers, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    datasets = []
                    for ds in data.get("datasets", []):
                        ref = ds.get("datasetReference", {})
                        datasets.append({
                            "datasetId": ref.get("datasetId"),
                            "projectId": ref.get("projectId"),
                            "friendlyName": ds.get("friendlyName"),
                            "location": ds.get("location"),
                        })
                    transformed = {
                        "datasets": datasets,
                        "nextPageToken": data.get("nextPageToken"),
                    }
                    return ToolResult(success=True, output=json.dumps(transformed), data=transformed)
                else:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("error", {}).get("message", "Failed to list BigQuery datasets")
                    except Exception:
                        error_msg = response.text or "Failed to list BigQuery datasets"
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")