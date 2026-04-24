from typing import Any, Dict
import httpx
from urllib.parse import quote, urlencode
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleBigQueryListTablesTool(BaseTool):
    name = "bigquery_list_tables"
    description = "List all tables in a Google BigQuery dataset"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="google_bigquery_access_token",
                description="OAuth access token for Google BigQuery",
                env_var="GOOGLE_BIGQUERY_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "google-bigquery",
            context=context,
            context_token_keys=("accessToken",),
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
                "datasetId": {
                    "type": "string",
                    "description": "BigQuery dataset ID",
                },
                "maxResults": {
                    "type": "number",
                    "description": "Maximum number of tables to return",
                },
                "pageToken": {
                    "type": "string",
                    "description": "Token for pagination",
                },
            },
            "required": ["projectId", "datasetId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        
        project_id = quote(parameters["projectId"])
        dataset_id = quote(parameters["datasetId"])
        url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{project_id}/datasets/{dataset_id}/tables"
        
        query_params = {}
        max_results = parameters.get("maxResults")
        if max_results is not None:
            try:
                mr = int(float(max_results))
                if mr > 0:
                    query_params["maxResults"] = str(mr)
            except (ValueError, TypeError):
                pass
        page_token = parameters.get("pageToken")
        if page_token:
            query_params["pageToken"] = str(page_token)
        
        if query_params:
            url += "?" + urlencode(query_params)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")