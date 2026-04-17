from typing import Any, Dict
import asyncpg
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class PostgreSQLUpdateTool(BaseTool):
    name = "postgresql_update"
    description = "Update data in PostgreSQL database"
    category = "integration"

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return []

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "host": {
                    "type": "string",
                    "description": "PostgreSQL server hostname or IP address",
                },
                "port": {
                    "type": "number",
                    "description": "PostgreSQL server port (default: 5432)",
                },
                "database": {
                    "type": "string",
                    "description": "Database name to connect to",
                },
                "username": {
                    "type": "string",
                    "description": "Database username",
                },
                "password": {
                    "type": "string",
                    "description": "Database password",
                },
                "ssl": {
                    "type": "string",
                    "description": "SSL connection mode (disabled, required, preferred)",
                },
                "table": {
                    "type": "string",
                    "description": "Table name to update data in",
                },
                "data": {
                    "type": "object",
                    "description": "Data object with fields to update (key-value pairs)",
                },
                "where": {
                    "type": "string",
                    "description": "WHERE clause condition (without WHERE keyword)",
                },
            },
            "required": [
                "host",
                "port",
                "database",
                "username",
                "password",
                "table",
                "data",
                "where",
            ],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        try:
            host = parameters["host"]
            port = parameters["port"]
            database = parameters["database"]
            username = parameters["username"]
            password = parameters["password"]
            ssl_str = parameters.get("ssl", "required")
            table = parameters["table"]
            data = parameters["data"]
            where = parameters["where"]

            if not isinstance(data, dict) or len(data) == 0:
                return ToolResult(
                    success=False, output="", error="Data must be a non-empty object"
                )

            ssl_modes = {
                "disabled": asyncpg.SSLMode.disable,
                "required": asyncpg.SSLMode.require,
                "preferred": asyncpg.SSLMode.prefer,
            }
            sslmode = ssl_modes.get(ssl_str.lower(), asyncpg.SSLMode.require)

            conn = await asyncpg.connect(
                host=host,
                port=port,
                database=database,
                user=username,
                password=password,
                ssl=sslmode,
            )

            try:
                set_parts = [f'"{k}" = ${i + 1}' for i, k in enumerate(data.keys())]
                set_clause = ", ".join(set_parts)
                values = list(data.values())
                query = f'UPDATE "{table}" SET {set_clause} WHERE {where} RETURNING *'
                rows = await conn.fetch(query, *values)
                row_count = len(rows)
                rows_dicts = [dict(row) for row in rows]
                output_data = {
                    "message": f"Data updated successfully. {row_count} row(s) affected.",
                    "rows": rows_dicts,
                    "rowCount": row_count,
                }
                return ToolResult(
                    success=True,
                    output=json.dumps(output_data),
                    data=output_data,
                )
            finally:
                await conn.close()
        except asyncpg.exceptions.PostgresError as e:
            return ToolResult(
                success=False, output="", error=f"PostgreSQL error: {str(e)}"
            )
        except Exception as e:
            return ToolResult(
                success=False, output="", error=f"Unexpected error: {str(e)}"
            )