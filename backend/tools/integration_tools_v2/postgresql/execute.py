from typing import Any, Dict
import json
from psycopg import AsyncConnection
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class PostgresExecuteTool(BaseTool):
    name = "postgresql_execute"
    description = "Execute raw SQL query on PostgreSQL database"
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
                "query": {
                    "type": "string",
                    "description": "Raw SQL query to execute",
                },
            },
            "required": ["host", "port", "database", "username", "password", "query"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        try:
            ssl = parameters.get("ssl", "preferred")
            sslmode_map = {
                "disabled": "disable",
                "required": "require",
                "preferred": "prefer",
            }
            sslmode = sslmode_map.get(ssl, "prefer")

            conn_config = {
                "host": parameters["host"],
                "port": int(parameters["port"]),
                "dbname": parameters["database"],
                "user": parameters["username"],
                "password": parameters["password"],
                "sslmode": sslmode,
            }

            async with await AsyncConnection.connect(**conn_config) as conn:
                async with conn.cursor() as cur:
                    await cur.execute(parameters["query"])
                    rows = await cur.fetchall()
                    rowcount = cur.rowcount
                    rows_serialized = [dict(row) for row in rows]
                    message = f"Query executed successfully. {rowcount} row(s) affected."
                    data = {
                        "message": message,
                        "rows": rows_serialized,
                        "rowCount": rowcount,
                    }
                    return ToolResult(
                        success=True,
                        output=json.dumps(data),
                        data=data,
                    )
        except Exception as e:
            error_msg = f"PostgreSQL execute failed: {str(e)}"
            return ToolResult(success=False, output="", error=error_msg)