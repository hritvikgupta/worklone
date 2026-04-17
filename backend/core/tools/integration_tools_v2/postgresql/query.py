from typing import Any, Dict, List
import asyncpg
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class PostgreSQLQueryTool(BaseTool):
    name = "postgresql_query"
    description = "Execute a SELECT query on PostgreSQL database"
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
                    "description": "SQL SELECT query to execute",
                },
            },
            "required": ["host", "port", "database", "username", "password", "query"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        host: str = parameters["host"]
        port: int = int(parameters["port"])
        database: str = parameters["database"]
        username: str = parameters["username"]
        password: str = parameters["password"]
        ssl: str = parameters.get("ssl", "preferred")
        query: str = parameters["query"]

        try:
            async with asyncpg.connect(
                host=host,
                port=port,
                database=database,
                user=username,
                password=password,
                ssl=ssl != "disabled",
            ) as conn:
                rows = await conn.fetch(query)
                row_count = len(rows)

            result_data = {
                "message": f"Query executed successfully. {row_count} row(s) returned.",
                "rows": [dict(row) for row in rows],
                "rowCount": row_count,
            }
            output_str = json.dumps(result_data)
            return ToolResult(success=True, output=output_str, data=result_data)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"PostgreSQL query failed: {str(e)}")