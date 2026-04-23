from typing import Any, Dict
import httpx
import urllib.parse
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleBigQueryGetTableTool(BaseTool):
    name = "google_bigquery_get_table"
    description = "Get metadata and schema for a Google BigQuery table"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GOOGLE_BIGQUERY_ACCESS_TOKEN",
                description="Access token",
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
                "tableId": {
                    "type": "string",
                    "description": "BigQuery table ID",
                },
            },
            "required": ["projectId", "datasetId", "tableId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        
        url = (
            f"https://bigquery.googleapis.com/bigquery/v2/projects/"
            f"{urllib.parse.quote(parameters['projectId'])}/"
            f"datasets/{urllib.parse.quote(parameters['datasetId'])}/"
            f"tables/{urllib.parse.quote(parameters['tableId'])}"
        )
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")