import json
from typing import Any

import asyncpg

from backend.core.tools.system_tools.base import BaseTool, CredentialRequirement, ToolResult


class PostgreSQLIntrospectTool(BaseTool):
    name = "postgresql_introspect"
    description = "Introspect PostgreSQL schema, tables, columns, and foreign keys."
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
                "schema": {
                    "type": "string",
                    "description": "Schema to introspect (default: public)",
                },
            },
            "required": ["host", "port", "database", "username", "password"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        host = parameters["host"]
        port = int(parameters["port"])
        database = parameters["database"]
        username = parameters["username"]
        password = parameters["password"]
        ssl = parameters.get("ssl", "preferred")
        schema_name = parameters.get("schema", "public")

        tables_sql = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = $1
          AND table_type = 'BASE TABLE'
        ORDER BY table_name
        """

        columns_sql = """
        SELECT
            table_name,
            column_name,
            data_type,
            is_nullable,
            column_default
        FROM information_schema.columns
        WHERE table_schema = $1
        ORDER BY table_name, ordinal_position
        """

        foreign_keys_sql = """
        SELECT
            tc.table_name,
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name,
            tc.constraint_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
          ON ccu.constraint_name = tc.constraint_name
         AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND tc.table_schema = $1
        ORDER BY tc.table_name, kcu.column_name
        """

        try:
            conn = await asyncpg.connect(
                host=host,
                port=port,
                database=database,
                user=username,
                password=password,
                ssl=ssl != "disabled",
            )
            try:
                table_rows = await conn.fetch(tables_sql, schema_name)
                column_rows = await conn.fetch(columns_sql, schema_name)
                fk_rows = await conn.fetch(foreign_keys_sql, schema_name)
            finally:
                await conn.close()

            tables = [row["table_name"] for row in table_rows]
            columns_by_table: dict[str, list[dict[str, Any]]] = {}
            for row in column_rows:
                columns_by_table.setdefault(row["table_name"], []).append(
                    {
                        "name": row["column_name"],
                        "dataType": row["data_type"],
                        "isNullable": row["is_nullable"] == "YES",
                        "default": row["column_default"],
                    }
                )

            fks_by_table: dict[str, list[dict[str, Any]]] = {}
            for row in fk_rows:
                fks_by_table.setdefault(row["table_name"], []).append(
                    {
                        "column": row["column_name"],
                        "referencesTable": row["foreign_table_name"],
                        "referencesColumn": row["foreign_column_name"],
                        "constraint": row["constraint_name"],
                    }
                )

            data = {
                "schema": schema_name,
                "database": database,
                "tableCount": len(tables),
                "tables": [
                    {
                        "name": table_name,
                        "columns": columns_by_table.get(table_name, []),
                        "foreignKeys": fks_by_table.get(table_name, []),
                    }
                    for table_name in tables
                ],
            }
            return ToolResult(success=True, output=json.dumps(data), data=data)
        except Exception as e:
            return ToolResult(success=False, output="", error=f"PostgreSQL introspection failed: {str(e)}")
