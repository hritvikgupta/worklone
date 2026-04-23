from typing import Any, Dict
import httpx
import json
from urllib.parse import quote
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleBigQueryQueryTool(BaseTool):
    name = "google_bigquery_query"
    description = "Run a SQL query against Google BigQuery and return the results"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GOOGLE_BIGQUERY_ACCESS_TOKEN",
                description="OAuth access token",
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
                "query": {
                    "type": "string",
                    "description": "SQL query to execute",
                },
                "useLegacySql": {
                    "type": "boolean",
                    "description": "Whether to use legacy SQL syntax (default: false)",
                },
                "maxResults": {
                    "type": "number",
                    "description": "Maximum number of rows to return",
                },
                "defaultDatasetId": {
                    "type": "string",
                    "description": "Default dataset for unqualified table names",
                },
                "location": {
                    "type": "string",
                    "description": "Processing location (e.g., \"US\", \"EU\")",
                },
            },
            "required": ["projectId", "query"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        project_id = parameters["projectId"]
        query_str = parameters["query"]
        url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{quote(project_id)}/queries"
        
        body: Dict[str, Any] = {
            "query": query_str,
            "useLegacySql": parameters.get("useLegacySql", False),
        }
        max_results = parameters.get("maxResults")
        if max_results is not None:
            body["maxResults"] = float(max_results)
        default_dataset_id = parameters.get("defaultDatasetId")
        if default_dataset_id:
            body["defaultDataset"] = {
                "projectId": project_id,
                "datasetId": default_dataset_id,
            }
        location = parameters.get("location")
        if location:
            body["location"] = location
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                try:
                    data = response.json()
                except:
                    return ToolResult(success=False, output=response.text, error="Invalid JSON response from BigQuery API")
                
                if response.status_code != 200:
                    error_message = ""
                    error_obj = data.get("error")
                    if isinstance(error_obj, dict):
                        error_message = error_obj.get("message", "")
                    if not error_message:
                        error_message = "Failed to execute BigQuery query"
                    return ToolResult(success=False, output="", error=error_message)
                
                columns = [f["name"] for f in data.get("schema", {}).get("fields", [])]
                rows = []
                for row in data.get("rows", []):
                    row_fields = row.get("f", [])
                    obj: Dict[str, Any] = {}
                    for index, field in enumerate(row_fields):
                        if index < len(columns):
                            v = field.get("v")
                            obj[columns[index]] = v if v is not None else None
                    rows.append(obj)
                
                transformed = {
                    "columns": columns,
                    "rows": rows,
                    "totalRows": data.get("totalRows"),
                    "jobComplete": data.get("jobComplete"),
                    "totalBytesProcessed": data.get("totalBytesProcessed"),
                    "cacheHit": data.get("cacheHit"),
                    "jobReference": data.get("jobReference"),
                    "pageToken": data.get("pageToken"),
                }
                
                output_str = json.dumps(transformed, default=str, indent=2)
                return ToolResult(success=True, output=output_str, data=transformed)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")