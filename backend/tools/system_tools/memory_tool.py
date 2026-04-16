"""
Memory Tool — lightweight persistent employee notes.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from backend.tools.system_tools.base import BaseTool, ToolResult


class MemoryTool(BaseTool):
    """Store and retrieve lightweight persistent notes for an employee."""

    name = "memory_store"
    description = "Save, retrieve, list, search, and delete persistent employee notes."
    category = "core"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["save_note", "list_notes", "get_note", "search_notes", "delete_note"],
                },
                "title": {"type": "string"},
                "content": {"type": "string"},
                "note_id": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "query": {"type": "string"},
            },
            "required": ["action"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        action = parameters.get("action")
        employee_id = (context or {}).get("employee_id") or "global"
        notes = self._load_notes(employee_id)

        if action == "save_note":
            note = {
                "id": parameters.get("note_id") or f"note_{uuid4().hex[:12]}",
                "title": parameters.get("title", "").strip() or "Untitled note",
                "content": parameters.get("content", ""),
                "tags": parameters.get("tags", []),
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            existing = next((idx for idx, item in enumerate(notes) if item["id"] == note["id"]), None)
            if existing is None:
                notes.append(note)
            else:
                note["created_at"] = notes[existing].get("created_at", note["created_at"])
                notes[existing] = note
            self._save_notes(employee_id, notes)
            return ToolResult(True, f"Saved note {note['id']}", data=note)

        if action == "list_notes":
            return ToolResult(True, json.dumps(notes[:100], indent=2), data={"notes": notes[:100]})

        if action == "get_note":
            note_id = parameters.get("note_id", "")
            note = next((item for item in notes if item["id"] == note_id), None)
            if not note:
                return ToolResult(False, "", error=f"Note not found: {note_id}")
            return ToolResult(True, json.dumps(note, indent=2), data=note)

        if action == "search_notes":
            query = parameters.get("query", "").lower().strip()
            if not query:
                return ToolResult(False, "", error="query is required")
            matches = [
                item for item in notes
                if query in item.get("title", "").lower()
                or query in item.get("content", "").lower()
                or any(query in tag.lower() for tag in item.get("tags", []))
            ]
            return ToolResult(True, json.dumps(matches[:50], indent=2), data={"notes": matches[:50]})

        if action == "delete_note":
            note_id = parameters.get("note_id", "")
            filtered = [item for item in notes if item["id"] != note_id]
            if len(filtered) == len(notes):
                return ToolResult(False, "", error=f"Note not found: {note_id}")
            self._save_notes(employee_id, filtered)
            return ToolResult(True, f"Deleted note {note_id}", data={"note_id": note_id})

        return ToolResult(False, "", error=f"Unknown action: {action}")

    def _memory_file(self, employee_id: str) -> Path:
        data_dir = Path(__file__).resolve().parents[2] / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir / f"memory_{employee_id}.json"

    def _load_notes(self, employee_id: str) -> list[dict]:
        path = self._memory_file(employee_id)
        if not path.exists():
            return []
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _save_notes(self, employee_id: str, notes: list[dict]) -> None:
        path = self._memory_file(employee_id)
        path.write_text(json.dumps(notes, indent=2), encoding="utf-8")
