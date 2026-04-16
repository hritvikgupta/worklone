"""
File Tool — basic workspace file operations for employees.
"""

from __future__ import annotations

from pathlib import Path

from backend.tools.system_tools.base import BaseTool, ToolResult


class FileTool(BaseTool):
    """Read, write, list, and search files in the workspace."""

    name = "file_operations"
    description = "Read, write, append, list, and search files in the workspace."
    category = "core"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "list_files",
                        "read_file",
                        "write_file",
                        "append_file",
                        "make_directory",
                        "search_files",
                        "search_text",
                    ],
                },
                "path": {"type": "string", "description": "Relative path inside the workspace"},
                "content": {"type": "string", "description": "File content for write/append operations"},
                "pattern": {"type": "string", "description": "Filename glob or text pattern to search for"},
                "recursive": {"type": "boolean", "default": True},
                "max_results": {"type": "integer", "default": 50},
                "max_chars": {"type": "integer", "default": 12000},
            },
            "required": ["action"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        action = parameters.get("action")
        root = Path((context or {}).get("workspace_root") or ".").resolve()
        path = self._resolve_path(root, parameters.get("path", ""))
        max_results = max(1, min(int(parameters.get("max_results", 50)), 200))
        max_chars = max(200, min(int(parameters.get("max_chars", 12000)), 50000))

        try:
            if action == "list_files":
                target = path if parameters.get("path") else root
                if not target.exists():
                    return ToolResult(False, "", error=f"Path not found: {target}")
                entries = sorted(target.rglob("*") if parameters.get("recursive", True) else target.iterdir())
                items = [str(p.relative_to(root)) for p in entries[:max_results]]
                return ToolResult(True, "\n".join(items) or "(no files)", data={"files": items})

            if action == "read_file":
                if not path.is_file():
                    return ToolResult(False, "", error=f"File not found: {path}")
                content = path.read_text(encoding="utf-8")
                return ToolResult(True, content[:max_chars], data={"path": str(path), "truncated": len(content) > max_chars})

            if action == "write_file":
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(parameters.get("content", ""), encoding="utf-8")
                return ToolResult(True, f"Wrote {path.relative_to(root)}", data={"path": str(path)})

            if action == "append_file":
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("a", encoding="utf-8") as handle:
                    handle.write(parameters.get("content", ""))
                return ToolResult(True, f"Appended to {path.relative_to(root)}", data={"path": str(path)})

            if action == "make_directory":
                path.mkdir(parents=True, exist_ok=True)
                return ToolResult(True, f"Created directory {path.relative_to(root)}", data={"path": str(path)})

            if action == "search_files":
                pattern = parameters.get("pattern", "*")
                matches = [str(p.relative_to(root)) for p in root.rglob(pattern) if p.is_file()][:max_results]
                return ToolResult(True, "\n".join(matches) or "(no matches)", data={"files": matches})

            if action == "search_text":
                pattern = parameters.get("pattern", "")
                if not pattern:
                    return ToolResult(False, "", error="pattern is required for search_text")
                matches: list[str] = []
                for candidate in root.rglob("*"):
                    if not candidate.is_file():
                        continue
                    try:
                        text = candidate.read_text(encoding="utf-8")
                    except Exception:
                        continue
                    if pattern in text:
                        matches.append(str(candidate.relative_to(root)))
                    if len(matches) >= max_results:
                        break
                return ToolResult(True, "\n".join(matches) or "(no matches)", data={"files": matches})

            return ToolResult(False, "", error=f"Unknown action: {action}")
        except Exception as exc:
            return ToolResult(False, "", error=str(exc))

    def _resolve_path(self, root: Path, relative_path: str) -> Path:
        candidate = (root / relative_path).resolve()
        if candidate != root and root not in candidate.parents:
            raise ValueError("Path must stay inside the workspace root")
        return candidate
