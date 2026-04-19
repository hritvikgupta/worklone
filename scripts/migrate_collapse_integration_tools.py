"""One-time migration: collapse granular integration-tool rows in employee_tools
to their provider bundle root.

Before: employee_tools has rows like (tool_name="GmailSearchTool"), (tool_name="GmailDraftTool"), ...
After:  a single row (tool_name="GmailTool") — which expand_tool_selection will
        fan back out at runtime, and which the Tools tab UI can render as
        "selected" so the user can untick it.

Idempotent. Safe to re-run.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.db.database import get_connection, get_shared_db_path
from backend.core.tools.catalog import (
    _BUNDLE_ALIAS_TO_ROOT,
    PROVIDER_TOOL_BUNDLES,
    create_tool,
)


# Build class-name -> bundle root map. PROVIDER_TOOL_BUNDLES members use runtime
# names (e.g. "gmail_search"); employee_tools.tool_name mostly stores class names
# (e.g. "GmailSearchTool"). Walk each bundle and instantiate members to get the
# class name off the resulting tool.
_CLASSNAME_TO_ROOT: dict[str, str] = {}
for _root, _bundle in PROVIDER_TOOL_BUNDLES.items():
    for _runtime_name in _bundle["members"]:
        _t = create_tool(_runtime_name)
        if _t is not None:
            _CLASSNAME_TO_ROOT[type(_t).__name__] = _root


def collapse(name: str) -> str | None:
    if not name:
        return None
    stripped = name.strip()
    if stripped in _CLASSNAME_TO_ROOT:
        return _CLASSNAME_TO_ROOT[stripped]
    root = _BUNDLE_ALIAS_TO_ROOT.get(stripped.lower())
    if root and root in PROVIDER_TOOL_BUNDLES and root != stripped:
        return root
    return None


def main() -> None:
    conn = get_connection(get_shared_db_path())
    cur = conn.cursor()
    cur.execute("SELECT id, employee_id, tool_name, is_enabled FROM employee_tools")
    rows = cur.fetchall()

    # Group by employee
    by_emp: dict[str, list[tuple]] = {}
    for r in rows:
        by_emp.setdefault(r["employee_id"], []).append(r)

    deletes: list[str] = []
    inserts: list[tuple[str, str]] = []  # (employee_id, root_name)

    for emp_id, emp_rows in by_emp.items():
        existing_names = {r["tool_name"] for r in emp_rows}
        needed_roots: set[str] = set()

        for r in emp_rows:
            root = collapse(r["tool_name"])
            if root:
                deletes.append(r["id"])
                if root not in existing_names:
                    needed_roots.add(root)

        for root in needed_roots:
            inserts.append((emp_id, root))

    if not deletes and not inserts:
        print("Nothing to migrate.")
        return

    print(f"Deleting {len(deletes)} granular rows, inserting {len(inserts)} bundle-root rows.")

    for row_id in deletes:
        cur.execute("DELETE FROM employee_tools WHERE id = ?", (row_id,))

    import uuid
    from datetime import datetime

    now = datetime.now().isoformat()
    for emp_id, root in inserts:
        cur.execute(
            "INSERT INTO employee_tools (id, employee_id, tool_name, is_enabled, config, created_at) "
            "VALUES (?, ?, ?, 1, '{}', ?)",
            (str(uuid.uuid4()), emp_id, root, now),
        )

    conn.commit()
    print("Done.")


if __name__ == "__main__":
    main()
