"""
SQL Tool — run SQLite queries and inspect schemas.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from backend.core.tools.system_tools.base import BaseTool, ToolResult


class SQLTool(BaseTool):
    """Run SQLite queries for analytics and operational tasks."""

    name = "run_sql"
    description = "Inspect SQLite schemas and run SQL queries against a SQLite database."
    category = "data"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["inspect_schema", "query"]},
                "db_path": {"type": "string", "description": "Path to a SQLite database file"},
                "sql": {"type": "string", "description": "SQL query to execute"},
                "params": {"type": "array", "items": {}},
                "limit": {"type": "integer", "default": 100},
                "allow_write": {"type": "boolean", "default": False},
            },
            "required": ["action", "db_path"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        action = parameters.get("action")
        root = Path((context or {}).get("workspace_root") or ".").resolve()
        db_path = (root / parameters.get("db_path", "")).resolve()
        if db_path != root and root not in db_path.parents:
            return ToolResult(False, "", error="db_path must stay inside the workspace root")
        if not db_path.exists():
            return ToolResult(False, "", error=f"Database not found: {db_path}")

        try:
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            if action == "inspect_schema":
                tables = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
                ).fetchall()
                payload = []
                for row in tables:
                    table = row["name"]
                    columns = conn.execute(f"PRAGMA table_info('{table}')").fetchall()
                    payload.append({
                        "table": table,
                        "columns": [
                            {"name": col["name"], "type": col["type"], "notnull": bool(col["notnull"])}
                            for col in columns
                        ],
                    })
                return ToolResult(True, json.dumps(payload, indent=2), data={"schema": payload})

            if action == "query":
                sql = parameters.get("sql", "").strip()
                if not sql:
                    return ToolResult(False, "", error="sql is required for query action")
                is_mutating = sql.split(None, 1)[0].upper() in {"INSERT", "UPDATE", "DELETE", "ALTER", "DROP", "CREATE", "REPLACE"}
                if is_mutating and not parameters.get("allow_write", False):
                    return ToolResult(False, "", error="Mutating SQL requires allow_write=true")
                rows = conn.execute(sql, parameters.get("params", [])).fetchall()
                limit = max(1, min(int(parameters.get("limit", 100)), 500))
                data = [dict(row) for row in rows[:limit]]
                if is_mutating:
                    conn.commit()
                return ToolResult(True, json.dumps(data, indent=2), data={"rows": data, "row_count": len(data)})

            return ToolResult(False, "", error=f"Unknown action: {action}")
        except Exception as exc:
            return ToolResult(False, "", error=str(exc))
        finally:
            try:
                conn.close()
            except Exception:
                pass
