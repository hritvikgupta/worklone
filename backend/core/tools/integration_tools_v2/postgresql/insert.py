from typing import Any, Dict, List
import asyncpg
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class PostgreSQLInsertTool(BaseTool):
    name = "postgresql_insert"
    description = "Insert data into PostgreSQL database"
    category = "integration"

    def get_required_credentials(self) -> List[CredentialRequirement]:
        return []

    def get_schema(self) -> Dict[str, Any]:
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
                    "enum": ["disabled", "required", "preferred"],
                },
                "table": {
                    "type": "string",
                    "description": "Table name to insert data into",
                },
                "data": {
                    "type": "object",
                    "description": "Data object to insert (key-value pairs)",
                },
            },
            "required": ["host", "port", "database", "username", "password", "table", "data"],
        }

    async def execute(self, parameters: Dict[str, Any], context: Dict[str, Any] | None = None) -> ToolResult:
        try:
            host = parameters["host"]
            port = parameters["port"]
            database = parameters["database"]
            username = parameters["username"]
            password = parameters["password"]
            ssl_mode = parameters.get("ssl", "preferred")
            table = parameters["table"]
            data = parameters["data"]

            ssl = ssl_mode != "disabled"

            conn = await asyncpg.connect(
                host=host,
                port=port,
                database=database,
                user=username,
                password=password,
                ssl=ssl,
            )

            columns = list(data.keys())
            if not columns:
                await conn.close()
                return ToolResult(success=False, output="", error="Data object cannot be empty")

            values = [data[col] for col in columns]
            columns_quoted = ', '.join(f'"{col}"' for col in columns)
            placeholders = ', '.join(f'${i + 1}' for i in range(len(columns)))
            query = f'INSERT INTO "{table}" ({columns_quoted}) VALUES ({placeholders}) RETURNING *'

            row = await conn.fetchrow(query, *values)
            await conn.close()

            row_count = 1 if row is not None else 0
            rows = [dict(row)] if row is not None else []
            message = f"Data inserted successfully. {row_count} row(s) affected."

            return ToolResult(
                success=True,
                output=message,
                data={
                    "message": message,
                    "rows": rows,
                    "rowCount": row_count,
                },
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"PostgreSQL insert failed: {str(e)}")