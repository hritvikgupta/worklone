from typing import Any, Dict
import httpx
import json
import urllib.parse
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleBigQueryInsertRowsTool(BaseTool):
    name = "BigQuery Insert Rows"
    description = "Insert rows into a Google BigQuery table using streaming insert"
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
                "rows": {
                    "type": "string",
                    "description": "JSON array of row objects to insert",
                },
                "skipInvalidRows": {
                    "type": "boolean",
                    "description": "Whether to insert valid rows even if some are invalid",
                },
                "ignoreUnknownValues": {
                    "type": "boolean",
                    "description": "Whether to ignore columns not in the table schema",
                },
            },
            "required": ["projectId", "datasetId", "tableId", "rows"],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        project_id = parameters["projectId"]
        dataset_id = parameters["datasetId"]
        table_id = parameters["tableId"]
        url = (
            f"https://bigquery.googleapis.com/bigquery/v2/projects/"
            f"{urllib.parse.quote(project_id)}/datasets/"
            f"{urllib.parse.quote(dataset_id)}/tables/"
            f"{urllib.parse.quote(table_id)}/insertAll"
        )

        try:
            parsed_rows = json.loads(parameters["rows"])
        except json.JSONDecodeError:
            return ToolResult(
                success=False,
                output="",
                error="Invalid JSON in rows parameter.",
            )

        rows_body = [{"json": row} for row in parsed_rows]
        body = {"rows": rows_body}
        skip_invalid_rows = parameters.get("skipInvalidRows")
        if skip_invalid_rows is not None:
            body["skipInvalidRows"] = skip_invalid_rows
        ignore_unknown_values = parameters.get("ignoreUnknownValues")
        if ignore_unknown_values is not None:
            body["ignoreUnknownValues"] = ignore_unknown_values

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200]:
                    try:
                        data = response.json()
                    except json.JSONDecodeError:
                        data = {}

                    insert_errors = data.get("insertErrors", [])
                    errors = []
                    for err in insert_errors:
                        errors.append(
                            {
                                "index": err["index"],
                                "errors": [
                                    {
                                        "reason": e.get("reason"),
                                        "location": e.get("location"),
                                        "message": e.get("message"),
                                    }
                                    for e in err.get("errors", [])
                                ],
                            }
                        )

                    total_rows = len(parsed_rows)
                    if len(insert_errors) == 0:
                        inserted_rows = total_rows
                    else:
                        failed_indexes = set(err["index"] for err in insert_errors)
                        inserted_rows = total_rows - len(failed_indexes)

                    result_data = {
                        "insertedRows": inserted_rows,
                        "errors": errors,
                    }
                    output_str = json.dumps(result_data)
                    return ToolResult(success=True, output=output_str, data=result_data)
                else:
                    try:
                        err_data = response.json()
                        error_msg = err_data.get("error", {}).get("message", response.text)
                    except json.JSONDecodeError:
                        error_msg = response.text
                    return ToolResult(success=False, output="", error=error_msg)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")