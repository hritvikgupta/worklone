"""
Team session memory tools — shared scratchpad scoped to a TeamRun (session).

These tools are ONLY registered when an agent is spawned inside a team run
(team_id + run_id present on the instance). They let every agent in the same
run read and write shared state keyed by `run_id`, so findings, decisions,
and artifacts survive even when agents hand off to each other.

Session lifetime == TeamRun lifetime. The run_id IS the session id.

Tools:
  - team_memory_write(key, value)       → insert/update a scratchpad entry
  - team_memory_read(key?)              → read one key or dump all entries
"""

from backend.core.tools.system_tools.base import BaseTool, ToolResult
from backend.db.stores.team_store import TeamStore


def _preview(text: str, limit: int = 300) -> str:
    if not text:
        return ""
    return text if len(text) <= limit else text[:limit] + "…"


class TeamMemoryWriteTool(BaseTool):
    name = "team_memory_write"
    description = (
        "Write or update a key in the SHARED team session scratchpad. "
        "Every teammate in this team run (session) can read it via team_memory_read. "
        "Use this to stash findings, decisions, artifacts, or handoff context that "
        "other agents in the same run need to see. "
        "Key is a short identifier (e.g. 'customer_gaps', 'final_report'). "
        "Value is the content (max 16KB). Overwrites existing key. "
        "Only available during an active team run."
    )
    category = "employee"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "Short identifier for this entry (e.g. 'customer_gaps').",
                },
                "value": {
                    "type": "string",
                    "description": "Content to store. Max 16KB. Overwrites if key exists.",
                },
            },
            "required": ["key", "value"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        ctx = context or {}
        run_id = ctx.get("run_id", "")
        team_id = ctx.get("team_id", "")
        if not run_id or not team_id:
            return ToolResult(
                False, "",
                error="No active team run. This tool is only available during a team run.",
            )

        key = parameters.get("key", "")
        value = parameters.get("value", "")
        if not isinstance(key, str) or not key.strip():
            return ToolResult(False, "", error="`key` must be a non-empty string.")
        if not isinstance(value, str):
            value = str(value)

        store = TeamStore()
        ok, err = store.session_memory_write(
            run_id=run_id,
            key=key,
            value=value,
            author_id=ctx.get("employee_id", ""),
            author_name=ctx.get("employee_name", ""),
        )
        if not ok:
            return ToolResult(False, "", error=err)

        return ToolResult(
            success=True,
            output=f"Stored '{key.strip()[:200]}' in team session memory "
                   f"({len(value.encode('utf-8'))} bytes). "
                   f"Teammates can read it with team_memory_read.",
            data={"run_id": run_id, "key": key.strip()[:200], "bytes": len(value.encode("utf-8"))},
        )


class TeamMemoryReadTool(BaseTool):
    name = "team_memory_read"
    description = (
        "Read from the SHARED team session scratchpad. "
        "Pass a specific `key` to fetch one entry, or omit `key` to list all entries "
        "in this team run (session) with previews. "
        "Use this to pick up context written by teammates before re-deriving work. "
        "Only available during an active team run."
    )
    category = "employee"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "Key to read. Omit to list all keys in this session.",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        ctx = context or {}
        run_id = ctx.get("run_id", "")
        team_id = ctx.get("team_id", "")
        if not run_id or not team_id:
            return ToolResult(
                False, "",
                error="No active team run. This tool is only available during a team run.",
            )

        store = TeamStore()
        key = parameters.get("key", "") or ""

        if key.strip():
            entry = store.session_memory_read(run_id, key)
            if not entry:
                return ToolResult(
                    success=True,
                    output=f"(no entry for key '{key.strip()}' in this session)",
                    data={"run_id": run_id, "key": key.strip(), "found": False},
                )
            lines = [
                f"=== team_memory['{entry['key']}'] ===",
                f"Author: {entry['author_name'] or entry['author_id'] or 'unknown'}",
                f"Updated: {entry['updated_at']}",
                f"",
                entry["value"],
            ]
            return ToolResult(
                success=True,
                output="\n".join(lines),
                data={"run_id": run_id, "entry": entry, "found": True},
            )

        # Full dump
        entries = store.session_memory_list(run_id)
        if not entries:
            return ToolResult(
                success=True,
                output="(team session scratchpad is empty — no entries yet)",
                data={"run_id": run_id, "entries": []},
            )

        lines = [f"=== Team Session Memory ({len(entries)} entries) ==="]
        for e in entries:
            lines.append(
                f"\n[{e['key']}] by {e['author_name'] or 'unknown'} "
                f"(updated {e['updated_at']}):\n{_preview(e['value'], 400)}"
            )
        return ToolResult(
            success=True,
            output="\n".join(lines),
            data={"run_id": run_id, "entries": entries},
        )
