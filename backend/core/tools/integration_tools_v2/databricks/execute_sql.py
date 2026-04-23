from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class DatabricksExecuteSqlTool(BaseTool):
    name = "databricks_execute_sql"
    description = "Execute a SQL statement against a Databricks SQL warehouse and return results inline. Supports parameterized queries and Unity Catalog."
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

    def _clean_host(self, host: str) -> str:
        if host.startswith("http://"):
            host = host[7:]
        elif host.startswith("https://"):
            host = host[8:]
        return host.rstrip("/")

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "host": {
                    "type": "string",
                    "description": "Databricks workspace host (e.g., dbc-abc123.cloud.databricks.com)",
                },
                "warehouseId": {
                    "type": "string",
                    "description": "The ID of the SQL warehouse to execute against",
                },
                "statement": {
                    "type": "string",
                    "description": "The SQL statement to execute (max 16 MiB)",
                },
                "catalog": {
                    "type": "string",
                    "description": "Unity Catalog name (equivalent to USE CATALOG)",
                },
                "schema": {
                    "type": "string",
                    "description": "Schema name (equivalent to USE SCHEMA)",
                },
                "rowLimit": {
                    "type": "number",
                    "description": "Maximum number of rows to return",
                },
                "waitTimeout": {
                    "type": "string",
                    "description": 'How long to wait for results (e.g., "50s"). Range: "0s" or "5s" to "50s". Default: "50s"',
                },
            },
            "required": ["host", "warehouseId", "statement"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        host = self._clean_host(parameters["host"])
        url = f"https://{host}/api/2.0/sql/statements/"

        body: Dict[str, Any] = {
            "warehouse_id": parameters["warehouseId"],
            "statement": parameters["statement"],
            "format": "JSON_ARRAY",
            "disposition": "INLINE",
            "wait_timeout": parameters.get("waitTimeout", "50s"),
        }
        if "catalog" in parameters:
            body["catalog"] = parameters["catalog"]
        if "schema" in parameters:
            body["schema"] = parameters["schema"]
        if "rowLimit" in parameters:
            body["row_limit"] = parameters["rowLimit"]

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, headers=headers, json=body)

                try:
                    resp_data = response.json()
                except Exception:
                    resp_data = {"error": response.text}

                if response.status_code >= 400:
                    error_msg = (
                        resp_data.get("message")
                        or resp_data.get("error", {}).get("message")
                        or resp_data.get("error")
                        or response.text
                    )
                    return ToolResult(success=False, output="", error=error_msg)

                status = resp_data.get("status", {}).get("state", "UNKNOWN")
                if status == "FAILED":
                    err = resp_data.get("status", {}).get("error", {})
                    error_msg = (
                        err.get("message")
                        or f"SQL statement execution failed: {err.get('error_code', 'UNKNOWN')}"
                    )
                    return ToolResult(success=False, output="", error=error_msg)

                statement_id = resp_data.get("statement_id", "")
                columns_raw = resp_data.get("manifest", {}).get("schema", {}).get("columns", [])
                columns = None
                if columns_raw:
                    columns = [
                        {
                            "name": col.get("name", ""),
                            "position": col.get("position", 0),
                            "typeName": col.get("type_name", ""),
                        }
                        for col in columns_raw
                    ]
                data_array = resp_data.get("result", {}).get("data_array", None)
                total_rows = resp_data.get("manifest", {}).get("total_row_count", None)
                truncated = resp_data.get("manifest", {}).get("truncated", False)

                transformed = {
                    "statementId": statement_id,
                    "status": status,
                    "columns": columns,
                    "data": data_array,
                    "totalRows": total_rows,
                    "truncated": truncated,
                }

                num_rows = len(data_array) if data_array else 0
                output_str = (
                    f"Statement ID: {statement_id}. Status: {status}. "
                    f"Retrieved {num_rows} rows "
                    f"(total: {total_rows if total_rows is not None else 'unknown'}). "
                    f"Truncated: {truncated}."
                )

                return ToolResult(success=True, output=output_str, data=transformed)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")