"""
Document tools — let an employee list and read the documents attached to it.

Two tools are exposed:

  - list_my_documents   → enumerate every document currently attached to the
                          employee (employee.memory) plus, when the agent is
                          running as part of a team session, the documents
                          attached to the team (team.attached_files).

  - read_my_document    → read the full content of one attached document,
                          identified by its storage path. Access is gated:
                          the path must appear in the employee's own memory
                          attachments, OR (team-run only) in the team's
                          attached_files list. Any other path is refused.

Both tools are registered as default employee tools so every agent has them.
The team branch is only *usable* when team_id + run_id are present in the
execution context; the tools themselves are always available.

Attachments are stored through FileStore under scope="agent", the same scope
the UI uses for the "Memory" / "Attach file" pickers in both the employee and
team config panels.
"""

from typing import Any, Dict, List, Optional

from backend.db.stores.employee_store import EmployeeStore
from backend.db.stores.file_store import FileStore
from backend.db.stores.team_store import TeamStore
from backend.core.tools.system_tools.base import BaseTool, ToolResult

# Scope used by the agent file browser (matches frontend getMarkdownTree('agent')
# and the /files/tree?scope=agent endpoint). Both employee.memory entries and
# team.attached_files entries are paths inside this scope.
_DOC_SCOPE = "agent"

# Extensions we are willing to decode as text in read_my_document.
_TEXT_EXTENSIONS = {
    ".md", ".markdown", ".mdx",
    ".txt", ".rst",
    ".json", ".yaml", ".yml", ".toml", ".csv", ".tsv",
    ".py", ".js", ".ts", ".tsx", ".jsx",
    ".html", ".css", ".sql", ".sh", ".env",
    ".log",
}


def _resolve_identifiers(context: Optional[dict]) -> Dict[str, str]:
    ctx = context or {}
    return {
        "user_id": ctx.get("user_id") or "",
        "owner_id": ctx.get("owner_id") or "",
        "employee_id": ctx.get("employee_id") or "",
        "employee_name": ctx.get("employee_name") or "",
        "team_id": ctx.get("team_id") or "",
        "run_id": ctx.get("run_id") or "",
    }


def _load_employee_paths(owner_id: str, employee_id: str) -> List[str]:
    if not employee_id:
        return []
    store = EmployeeStore()
    employee = store.get_employee(employee_id, owner_id)
    if not employee:
        return []
    paths = [p for p in (employee.memory or []) if isinstance(p, str) and p.strip()]
    # De-dupe while preserving order
    seen = set()
    unique: List[str] = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return unique


def _load_team_paths(owner_id: str, team_id: str) -> List[str]:
    if not team_id:
        return []
    store = TeamStore()
    team = store.get_team(team_id, owner_id)
    if not team:
        return []
    paths = [p for p in (team.attached_files or []) if isinstance(p, str) and p.strip()]
    seen = set()
    unique: List[str] = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return unique


def _describe_document(file_store: FileStore, user_id: str, path: str) -> Dict[str, Any]:
    meta = file_store.get_file_metadata(user_id, _DOC_SCOPE, path)
    if not meta:
        return {
            "path": path,
            "name": path.split("/")[-1] or path,
            "exists": False,
            "type": None,
        }
    return {
        "path": meta["path"],
        "name": meta["name"],
        "exists": True,
        "type": meta["type"],
    }


def _is_text_path(path: str) -> bool:
    lower = path.lower()
    for ext in _TEXT_EXTENSIONS:
        if lower.endswith(ext):
            return True
    # Files with no extension are optimistically treated as text.
    return "." not in lower.rsplit("/", 1)[-1]


class ListMyDocumentsTool(BaseTool):
    name = "list_my_documents"
    description = (
        "List every document currently attached to you as reference material. "
        "Always returns your own employee-level attachments (set via the Memory "
        "tab on your profile). When you are running as part of a team session, "
        "the response additionally includes the team's shared attached documents "
        "so you can read anything the team owner made available. "
        "Use this first to discover what reference material you can consult, "
        "then call read_my_document with the path you want to read."
    )
    category = "employee"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {},
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        ids = _resolve_identifiers(context)
        user_id = ids["user_id"]
        owner_id = ids["owner_id"]
        employee_id = ids["employee_id"]
        team_id = ids["team_id"]
        run_id = ids["run_id"]

        if not user_id or not employee_id:
            return ToolResult(
                success=False,
                output="",
                error="Missing employee identity in tool context; cannot list documents.",
            )

        file_store = FileStore()

        employee_paths = _load_employee_paths(owner_id, employee_id)
        employee_docs = [_describe_document(file_store, user_id, p) for p in employee_paths]

        in_team_run = bool(team_id and run_id)
        team_paths: List[str] = []
        team_docs: List[Dict[str, Any]] = []
        if in_team_run:
            team_paths = _load_team_paths(owner_id, team_id)
            team_docs = [_describe_document(file_store, user_id, p) for p in team_paths]

        lines: List[str] = []
        lines.append(
            f"=== Documents attached to {ids['employee_name'] or 'you'} ==="
        )
        if employee_docs:
            lines.append(f"MY DOCUMENTS ({len(employee_docs)}):")
            for d in employee_docs:
                status = "" if d["exists"] else "  [missing in storage]"
                lines.append(f"  - {d['path']}  ({d['type'] or 'unknown'}){status}")
        else:
            lines.append("MY DOCUMENTS: none attached to this employee.")

        if in_team_run:
            lines.append("")
            if team_docs:
                lines.append(
                    f"TEAM DOCUMENTS ({len(team_docs)}) — shared with the whole team run {run_id}:"
                )
                for d in team_docs:
                    status = "" if d["exists"] else "  [missing in storage]"
                    lines.append(f"  - {d['path']}  ({d['type'] or 'unknown'}){status}")
            else:
                lines.append(
                    f"TEAM DOCUMENTS: none attached to team {team_id}."
                )
        else:
            lines.append("")
            lines.append(
                "TEAM DOCUMENTS: not in a team run — no team-level attachments available."
            )

        lines.append("")
        lines.append(
            "To read a document, call read_my_document(path='<exact path above>')."
        )

        return ToolResult(
            success=True,
            output="\n".join(lines),
            data={
                "employee_id": employee_id,
                "team_id": team_id if in_team_run else "",
                "run_id": run_id if in_team_run else "",
                "in_team_run": in_team_run,
                "employee_documents": employee_docs,
                "team_documents": team_docs,
            },
        )


class ReadMyDocumentTool(BaseTool):
    name = "read_my_document"
    description = (
        "Read the full text content of one document attached to you. The path "
        "must be one of the documents returned by list_my_documents — either "
        "attached to you directly (your own memory) or, when you are in a team "
        "run, attached to your team. Paths outside of that allow-list are "
        "refused. Only text-like files (markdown, txt, json, yaml, code, etc.) "
        "can be read through this tool."
    )
    category = "employee"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": (
                        "Exact storage path of the document to read, as shown "
                        "by list_my_documents (e.g. 'agent/briefs/launch.md')."
                    ),
                },
                "source": {
                    "type": "string",
                    "enum": ["auto", "employee", "team"],
                    "description": (
                        "Where to look for the path. 'employee' restricts to "
                        "your own memory, 'team' restricts to the team's "
                        "attached files (team run only), 'auto' (default) "
                        "checks both."
                    ),
                },
            },
            "required": ["path"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        path = (parameters.get("path") or "").strip()
        source = (parameters.get("source") or "auto").strip().lower()
        if source not in ("auto", "employee", "team"):
            source = "auto"

        if not path:
            return ToolResult(
                success=False, output="",
                error="Parameter 'path' is required.",
            )

        ids = _resolve_identifiers(context)
        user_id = ids["user_id"]
        owner_id = ids["owner_id"]
        employee_id = ids["employee_id"]
        team_id = ids["team_id"]
        run_id = ids["run_id"]
        in_team_run = bool(team_id and run_id)

        if not user_id or not employee_id:
            return ToolResult(
                success=False, output="",
                error="Missing employee identity in tool context; cannot read document.",
            )

        check_employee = source in ("auto", "employee")
        check_team = source in ("auto", "team") and in_team_run

        if source == "team" and not in_team_run:
            return ToolResult(
                success=False, output="",
                error="source='team' requires an active team run.",
            )

        employee_paths = _load_employee_paths(owner_id, employee_id) if check_employee else []
        team_paths = _load_team_paths(owner_id, team_id) if check_team else []

        matched_source: Optional[str] = None
        if check_employee and path in employee_paths:
            matched_source = "employee"
        elif check_team and path in team_paths:
            matched_source = "team"

        if not matched_source:
            scopes_checked = []
            if check_employee:
                scopes_checked.append("your employee memory")
            if check_team:
                scopes_checked.append(f"team {team_id} attached files")
            where = " or ".join(scopes_checked) if scopes_checked else "any allowed source"
            return ToolResult(
                success=False, output="",
                error=(
                    f"Path '{path}' is not attached to {where}. "
                    f"Call list_my_documents to see the documents you can read."
                ),
            )

        if not _is_text_path(path):
            return ToolResult(
                success=False, output="",
                error=(
                    f"Path '{path}' is not a text-readable file. "
                    f"read_my_document only supports text/markdown/code files."
                ),
            )

        file_store = FileStore()
        meta = file_store.get_file_metadata(user_id, _DOC_SCOPE, path)
        if not meta or meta["type"] != "file":
            return ToolResult(
                success=False, output="",
                error=f"Document '{path}' is not a file in storage (or was deleted).",
            )

        content = file_store.read_file_content(user_id, _DOC_SCOPE, path)
        if content is None:
            return ToolResult(
                success=False, output="",
                error=f"Failed to read document content for '{path}'.",
            )

        header = (
            f"=== {meta['name']} ===\n"
            f"Path:   {meta['path']}\n"
            f"Source: {matched_source} attachment\n"
            f"Size:   {len(content)} characters\n"
            f"---\n"
        )

        return ToolResult(
            success=True,
            output=header + content,
            data={
                "path": meta["path"],
                "name": meta["name"],
                "source": matched_source,
                "content": content,
                "length": len(content),
            },
        )
