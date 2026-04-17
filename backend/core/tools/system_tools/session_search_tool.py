"""Session Search Tool — search prior chat/workflow conversation history for a user."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from backend.core.tools.system_tools.base import BaseTool, ToolResult
from backend.db.database import get_connection, get_shared_db_path


class SessionSearchTool(BaseTool):
    """Search a user's previous sessions/messages with lightweight SQL matching."""

    name = "session_search"
    description = (
        "Search previous sessions and messages for this user. "
        "If query is omitted, returns recent sessions."
    )
    category = "core"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Keywords or phrase to search for. Omit to list recent sessions.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum sessions to return (1-25). Default 5.",
                },
                "source": {
                    "type": "string",
                    "enum": ["all", "chat", "workflow"],
                    "description": "Where to search. Default 'all'.",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        ctx = context or {}
        owner_id = (ctx.get("owner_id") or ctx.get("user_id") or "").strip()
        employee_id = (ctx.get("employee_id") or "").strip()
        if not owner_id:
            return ToolResult(False, "", error="No user context found for session search.")

        raw_limit = parameters.get("limit", 5)
        try:
            limit = max(1, min(25, int(raw_limit)))
        except Exception:
            limit = 5

        source = (parameters.get("source") or "chat").strip().lower()
        if source not in {"all", "chat", "workflow"}:
            source = "chat"

        query = (parameters.get("query") or "").strip()

        conn = get_connection(get_shared_db_path())
        try:
            if not query:
                sessions = self._recent_sessions(conn, owner_id, employee_id, source, limit)
                if not sessions:
                    return ToolResult(True, "No previous sessions found.", data={"sessions": []})

                lines = [f"Recent sessions ({len(sessions)}):"]
                for idx, row in enumerate(sessions, start=1):
                    title = row.get("title") or "Untitled"
                    preview = (row.get("preview") or "").replace("\n", " ").strip()
                    if len(preview) > 140:
                        preview = preview[:140] + "..."
                    lines.append(
                        f"{idx}. [{row['source']}] {title} (id={row['session_id']}, updated={row['updated_at']})"
                    )
                    if preview:
                        lines.append(f"   Preview: {preview}")

                return ToolResult(True, "\n".join(lines), data={"sessions": sessions})

            sessions = self._search_sessions(conn, owner_id, employee_id, source, query, limit)
            if not sessions:
                return ToolResult(
                    True,
                    f"No matching sessions found for query: '{query}'.",
                    data={"query": query, "sessions": []},
                )

            lines = [f"Search results for '{query}' ({len(sessions)} session matches):"]
            for idx, row in enumerate(sessions, start=1):
                title = row.get("title") or "Untitled"
                lines.append(
                    f"{idx}. [{row['source']}] {title} (id={row['session_id']}, hits={row['hit_count']}, last={row['last_match_at']})"
                )
                snippet = (row.get("snippet") or "").replace("\n", " ").strip()
                if len(snippet) > 180:
                    snippet = snippet[:180] + "..."
                if snippet:
                    lines.append(f"   Snippet: {snippet}")

            return ToolResult(
                True,
                "\n".join(lines),
                data={"query": query, "sessions": sessions},
            )
        finally:
            conn.close()

    def _recent_sessions(
        self,
        conn,
        owner_id: str,
        employee_id: str,
        source: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []

        if source in {"all", "chat"}:
            if employee_id:
                chat_rows = conn.execute(
                    """
                    SELECT
                        s.id AS session_id,
                        COALESCE(s.title, '') AS title,
                        COALESCE(s.updated_at, s.created_at, '') AS updated_at,
                        COALESCE(m.content, '') AS preview
                    FROM chat_sessions s
                    LEFT JOIN chat_messages m
                        ON m.id = (
                            SELECT id
                            FROM chat_messages
                            WHERE session_id = s.id
                            ORDER BY id DESC
                            LIMIT 1
                        )
                    WHERE s.user_id = ? AND s.employee_id = ?
                    ORDER BY COALESCE(s.updated_at, s.created_at) DESC
                    LIMIT ?
                    """,
                    (owner_id, employee_id, limit),
                ).fetchall()
            else:
                chat_rows = conn.execute(
                    """
                    SELECT
                        s.id AS session_id,
                        COALESCE(s.title, '') AS title,
                        COALESCE(s.updated_at, s.created_at, '') AS updated_at,
                        COALESCE(m.content, '') AS preview
                    FROM chat_sessions s
                    LEFT JOIN chat_messages m
                        ON m.id = (
                            SELECT id
                            FROM chat_messages
                            WHERE session_id = s.id
                            ORDER BY id DESC
                            LIMIT 1
                        )
                    WHERE s.user_id = ?
                    ORDER BY COALESCE(s.updated_at, s.created_at) DESC
                    LIMIT ?
                    """,
                    (owner_id, limit),
                ).fetchall()
            for r in chat_rows:
                items.append({
                    "source": "chat",
                    "session_id": r["session_id"],
                    "title": r["title"],
                    "updated_at": r["updated_at"],
                    "preview": r["preview"],
                })

        if source in {"all", "workflow"}:
            wf_rows = conn.execute(
                """
                SELECT
                    c.id AS session_id,
                    COALESCE(c.title, '') AS title,
                    COALESCE(c.updated_at, c.created_at, '') AS updated_at,
                    COALESCE(m.content, '') AS preview
                FROM conversations c
                LEFT JOIN messages m
                    ON m.id = (
                        SELECT id
                        FROM messages
                        WHERE conversation_id = c.id
                        ORDER BY created_at DESC
                        LIMIT 1
                    )
                WHERE c.owner_id = ?
                ORDER BY COALESCE(c.updated_at, c.created_at) DESC
                LIMIT ?
                """,
                (owner_id, limit),
            ).fetchall()
            for r in wf_rows:
                items.append({
                    "source": "workflow",
                    "session_id": r["session_id"],
                    "title": r["title"],
                    "updated_at": r["updated_at"],
                    "preview": r["preview"],
                })

        items.sort(key=lambda x: x.get("updated_at") or "", reverse=True)
        return items[:limit]

    def _search_sessions(
        self,
        conn,
        owner_id: str,
        employee_id: str,
        source: str,
        query: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        q = f"%{query.lower()}%"
        grouped: dict[tuple[str, str], dict[str, Any]] = defaultdict(dict)

        if source in {"all", "chat"}:
            if employee_id:
                rows = conn.execute(
                    """
                    SELECT
                        s.id AS session_id,
                        COALESCE(s.title, '') AS title,
                        cm.content AS content,
                        cm.created_at AS created_at
                    FROM chat_messages cm
                    JOIN chat_sessions s ON s.id = cm.session_id
                    WHERE s.user_id = ? AND s.employee_id = ? AND LOWER(cm.content) LIKE ?
                    ORDER BY cm.created_at DESC
                    LIMIT ?
                    """,
                    (owner_id, employee_id, q, max(limit * 20, 100)),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT
                        s.id AS session_id,
                        COALESCE(s.title, '') AS title,
                        cm.content AS content,
                        cm.created_at AS created_at
                    FROM chat_messages cm
                    JOIN chat_sessions s ON s.id = cm.session_id
                    WHERE s.user_id = ? AND LOWER(cm.content) LIKE ?
                    ORDER BY cm.created_at DESC
                    LIMIT ?
                    """,
                    (owner_id, q, max(limit * 20, 100)),
                ).fetchall()
            self._accumulate(grouped, rows, "chat")

        if source in {"all", "workflow"}:
            rows = conn.execute(
                """
                SELECT
                    c.id AS session_id,
                    COALESCE(c.title, '') AS title,
                    m.content AS content,
                    m.created_at AS created_at
                FROM messages m
                JOIN conversations c ON c.id = m.conversation_id
                WHERE c.owner_id = ? AND LOWER(m.content) LIKE ?
                ORDER BY m.created_at DESC
                LIMIT ?
                """,
                (owner_id, q, max(limit * 20, 100)),
            ).fetchall()
            self._accumulate(grouped, rows, "workflow")

        results = list(grouped.values())
        results.sort(key=lambda r: r.get("last_match_at") or "", reverse=True)
        return results[:limit]

    def _accumulate(self, grouped: dict, rows, source: str) -> None:
        for r in rows:
            key = (source, r["session_id"])
            item = grouped.get(key)
            if not item:
                item = {
                    "source": source,
                    "session_id": r["session_id"],
                    "title": r["title"],
                    "hit_count": 0,
                    "last_match_at": r["created_at"] or "",
                    "snippet": r["content"] or "",
                }
                grouped[key] = item

            item["hit_count"] += 1
            created_at = r["created_at"] or ""
            if created_at > (item.get("last_match_at") or ""):
                item["last_match_at"] = created_at
                item["snippet"] = r["content"] or ""
