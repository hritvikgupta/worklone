import asyncpg
from typing import Any, Dict, List
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class PostgreSQLIntrospectTool(BaseTool):
    name = "postgresql_introspect"
    description = "Introspect PostgreSQL database schema to retrieve table structures, columns, and relationships"
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
                "