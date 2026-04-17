import json
import asyncpg
from typing import Any, Dict
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class PostgreSQLDeleteTool(BaseTool):
    name = "postgresql_delete"
    description = "Delete data from PostgreSQL database"
    category = "integration"

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return []

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "host": {
                    "type": "string",
                    "description": "PostgreSQL server hostname or IP address"
                },
                "port": {
                    "type": "number",
                    "description": "PostgreSQL server port (default: 5432)"
                },
                "database": {
                    "type": "string",
                    "description": "Database name to connect to"
                },
                "username": {
                    "type": "string",
                    "description": "Database username"
                },
                "password": {
                    "type": "string",
                    "description": "Database password"
                },
                "ssl": {
                    "type": "string",
                    "description": "SSL connection mode (disabled, required, preferred)"
                },
                "table": {
                    "type": "string",
                    "description": "Table name to delete data from"
                },
                "where": {
                    "type": "string",
                    "description": "WHERE clause condition (without WHERE keyword)"
                }
            },
            "required": ["host", "port", "database", "username", "password", "table", "where"]
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        try:
            host = parameters["host"]
            port = int(parameters["port"])
            database = parameters["database"]
            username = parameters["username"]
            password = parameters["password"]
            ssl_mode = parameters.get("ssl", "preferred")
            table = parameters["table"]
            where = parameters["where"]

            ssl_mapping = {
                "disabled": False,
                "required": True,
                "preferred": None,
            }
            ssl = ssl_mapping.get(ssl_mode, None)

            conn_params = {
                "host": host,
                "port": port,
                "database": database,
                "user": username,
                "password": password,
                "ssl": ssl,
            }

            async with asyncpg.connect(timeout=30.0, **conn_params) as conn:
                query = f"DELETE FROM {table} WHERE {where} RETURNING *"
                rows = await conn.fetch(query)
                row_count = len(rows)
                data = {
                    "message": f"Data deleted successfully. {row_count} row(s) affected.",
                    "rows": [dict(row) for row in rows],
                    "rowCount": row_count,
                }
                return ToolResult(success=True, output=json.dumps(data), data=data)
        except Exception as e:
            return ToolResult(success=False, output="", error=f"PostgreSQL delete failed: {str(e)}")