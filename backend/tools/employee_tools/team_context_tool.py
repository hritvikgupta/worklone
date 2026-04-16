"""
GetMyTeamContextTool — discovers team context for a team-run agent instance.

This tool is ONLY registered into an employee's tool registry when the agent
is spawned as part of a TeamRun (i.e. when team_id and run_id are present in
the instance context). Solo employees never see this tool.

When called, it returns:
  - The team goal for this run
  - The employee's own assigned task in this run
  - All teammates (name, role, employee_id)
  - The conversation_id for this team run (used for all inter-agent messages)
  - Recent conversation history for context

This is intentionally the FIRST tool a team agent should call — it gives them
everything they need to understand who they are in this run, what to do,
and who to talk to.
"""

from backend.tools.system_tools.base import BaseTool, ToolResult
from backend.store.team_store import TeamStore


class GetMyTeamContextTool(BaseTool):
    name = "get_my_team_context"
    description = (
        "Discover your team context for this run. Call this FIRST when you start working. "
        "Returns: your assigned task, team goal, all teammates with their names/roles/IDs, "
        "and the conversation_id you must use when messaging teammates. "
        "Only available when you are part of an active team run."
    )
    category = "employee"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "include_conversation": {
                    "type": "boolean",
                    "description": "Include the recent conversation history for this team run. Default true.",
                },
                "include_scratchpad": {
                    "type": "boolean",
                    "description": "Include the team session scratchpad (shared memory written by teammates via team_memory_write). Default true.",
                },
                "include_history": {
                    "type": "boolean",
                    "description": "Include summaries of the last 3 completed runs for this team (cross-session memory). Default true.",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        include_conversation = parameters.get("include_conversation", True)
        include_scratchpad = parameters.get("include_scratchpad", True)
        include_history = parameters.get("include_history", True)

        ctx = context or {}
        team_id = ctx.get("team_id", "")
        run_id = ctx.get("run_id", "")
        employee_id = ctx.get("employee_id", "")

        if not team_id or not run_id:
            return ToolResult(
                False, "",
                error="No active team run. This tool is only available during a team run.",
            )

        store = TeamStore()

        full_run = store.get_full_run(run_id)
        if not full_run:
            return ToolResult(False, "", error=f"Team run {run_id} not found")

        run = full_run["run"]
        all_members = full_run["members"]

        # Find this employee's assignment
        my_member = next((m for m in all_members if m.employee_id == employee_id), None)
        if not my_member:
            return ToolResult(
                False, "",
                error=f"Employee {employee_id} is not a member of run {run_id}",
            )

        # Build teammate list (everyone except self)
        teammates = [
            {
                "employee_id": m.employee_id,
                "name": m.employee_name,
                "role": m.employee_role,
                "task": m.assigned_task,
                "task_status": m.task_status.value,
            }
            for m in all_members
            if m.employee_id != employee_id
        ]

        # Optionally include recent conversation
        conversation_summary = []
        if include_conversation:
            messages = store.get_conversation(run.conversation_id, limit=20)
            conversation_summary = [
                {
                    "from": m.sender_name,
                    "to": m.recipient_name,
                    "message": m.content[:500],
                    "timestamp": m.created_at.isoformat(),
                }
                for m in messages
            ]

        output_lines = [
            f"=== Your Team Session (run {run_id}) ===",
            f"",
            f"TEAM GOAL: {run.goal}",
            f"",
            f"YOUR TASK: {my_member.assigned_task}",
            f"Session ID (run_id): {run_id}",
            f"Conversation ID: {run.conversation_id}",
            f"  (Use this conversation_id in ALL messages to teammates)",
            f"",
            f"YOUR TEAMMATES ({len(teammates)}):",
        ]
        for t in teammates:
            output_lines.append(
                f"  - {t['name']} ({t['role']}) | ID: {t['employee_id']} | Task: {t['task']} | Status: {t['task_status']}"
            )

        # ── Shared team session scratchpad (live state written by teammates) ──
        scratchpad_entries = []
        if include_scratchpad:
            scratchpad_entries = store.session_memory_list(run_id)
            if scratchpad_entries:
                output_lines += [
                    f"",
                    f"TEAM SESSION SCRATCHPAD ({len(scratchpad_entries)} entries — shared memory for this run):",
                    f"  (Use team_memory_read(key) for full value, team_memory_write(key, value) to add)",
                ]
                for e in scratchpad_entries[:20]:
                    preview = e["value"][:300] + ("…" if len(e["value"]) > 300 else "")
                    output_lines.append(
                        f"  • [{e['key']}] by {e['author_name'] or 'unknown'}: {preview}"
                    )
            else:
                output_lines += [
                    f"",
                    f"TEAM SESSION SCRATCHPAD: empty. Use team_memory_write(key, value) to share state with teammates.",
                ]

        # ── Recent conversation thread ──
        if conversation_summary:
            output_lines += [
                f"",
                f"RECENT CONVERSATION ({len(conversation_summary)} messages):",
            ]
            for msg in conversation_summary[-10:]:
                output_lines.append(
                    f"  [{msg['from']} -> {msg['to']}]: {msg['message'][:200]}"
                )
        elif include_conversation:
            output_lines += ["", "CONVERSATION: No messages yet — you are starting fresh."]

        # ── Cross-run history: last 3 completed runs for this team ──
        prior_runs_summary = []
        if include_history:
            prior = store.list_recent_completed_runs(team_id, limit=3, exclude_run_id=run_id)
            if prior:
                output_lines += [
                    f"",
                    f"PREVIOUS TEAM SESSIONS ({len(prior)} completed runs — what this team did before):",
                ]
                for p in prior:
                    p_run = p["run"]
                    p_members = p["members"]
                    output_lines.append(
                        f"  ── Run {p_run.id} | Goal: {p_run.goal[:120]} | Completed: {p_run.completed_at}"
                    )
                    for pm in p_members:
                        preview = (pm.result or "")[:250] + ("…" if pm.result and len(pm.result) > 250 else "")
                        output_lines.append(
                            f"     • {pm.employee_name} ({pm.task_status.value}): {preview}"
                        )
                    prior_runs_summary.append({
                        "run_id": p_run.id,
                        "goal": p_run.goal,
                        "completed_at": p_run.completed_at.isoformat() if p_run.completed_at else None,
                        "members": [
                            {
                                "employee_id": pm.employee_id,
                                "employee_name": pm.employee_name,
                                "task": pm.assigned_task,
                                "task_status": pm.task_status.value,
                                "result": pm.result,
                            }
                            for pm in p_members
                        ],
                    })

        return ToolResult(
            success=True,
            output="\n".join(output_lines),
            data={
                "run_id": run_id,
                "session_id": run_id,
                "team_id": team_id,
                "conversation_id": run.conversation_id,
                "goal": run.goal,
                "my_task": my_member.assigned_task,
                "my_task_status": my_member.task_status.value,
                "teammates": teammates,
                "conversation": conversation_summary,
                "scratchpad": scratchpad_entries,
                "previous_sessions": prior_runs_summary,
            },
        )
