from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException

from backend.db.database import get_connection, get_shared_db_path
from backend.db.stores.employee_store import EmployeeStore
from backend.lib.auth.session import get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

def get_db():
    return get_connection(get_shared_db_path())

def get_store():
    return EmployeeStore()

def _compute_employee_run_time(conn, employee_id: str) -> int:
    """
    Compute total run time in seconds for an employee across all work types:
    - employee_tasks: created_at → completed_at
    - sprint_runs: created_at → completed_at (or updated_at for completed runs without completed_at)
    - team_run_members: created_at → completed_at (or updated_at for done/blocked runs without completed_at)
    """
    total_seconds = 0

    # 1. Employee tasks with completed_at
    rows = conn.execute("""
        SELECT created_at, completed_at FROM employee_tasks
        WHERE employee_id = ? AND completed_at IS NOT NULL
    """, (employee_id,)).fetchall()
    for r in rows:
        try:
            start = datetime.fromisoformat(r["created_at"])
            end = datetime.fromisoformat(r["completed_at"])
            total_seconds += max(0, (end - start).total_seconds())
        except Exception:
            pass

    # 2. Sprint runs (completed = status in done/failed/completed)
    rows = conn.execute("""
        SELECT created_at, completed_at, updated_at, status FROM sprint_runs
        WHERE employee_id = ? AND status IN ('done', 'failed', 'completed')
    """, (employee_id,)).fetchall()
    for r in rows:
        try:
            start = datetime.fromisoformat(r["created_at"])
            end_str = r["completed_at"] or r["updated_at"]
            end = datetime.fromisoformat(end_str)
            total_seconds += max(0, (end - start).total_seconds())
        except Exception:
            pass

    # 3. Team run members (done/blocked)
    rows = conn.execute("""
        SELECT created_at, completed_at, updated_at, task_status FROM team_run_members
        WHERE employee_id = ? AND task_status IN ('done', 'blocked')
    """, (employee_id,)).fetchall()
    for r in rows:
        try:
            start = datetime.fromisoformat(r["created_at"])
            end_col = None
            try:
                end_col = r["completed_at"]
            except (IndexError, KeyError):
                pass
            end_str = end_col or r["updated_at"]
            end = datetime.fromisoformat(end_str)
            total_seconds += max(0, (end - start).total_seconds())
        except Exception:
            pass

    return int(total_seconds)


def _format_duration(seconds: int) -> str:
    if seconds >= 3600:
        return f"{seconds / 3600:.1f}h"
    elif seconds >= 60:
        return f"{seconds / 60:.1f}m"
    else:
        return f"{seconds}s"


@router.get("/stats")
async def get_dashboard_stats(
    user=Depends(get_current_user),
):
    """Get global dashboard stats (tokens, expenditure, uptime) from real data."""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    owner_id = str(user["id"])
    store = get_store()
    conn = get_db()

    # Token & cost from usage log
    usage = store.get_usage_stats(owner_id)
    total_tokens = usage["total_tokens"]
    total_cost = usage["total_cost"]
    total_calls = usage["total_calls"]

    # Run time: sum across all employees
    if owner_id:
        emp_rows = conn.execute(
            "SELECT id FROM employees WHERE owner_id = ?", (owner_id,)
        ).fetchall()
    else:
        emp_rows = conn.execute("SELECT id FROM employees").fetchall()
    total_run_seconds = 0
    for emp in emp_rows:
        total_run_seconds += _compute_employee_run_time(conn, emp["id"])

    # Active employees
    if owner_id:
        active_employees = conn.execute(
            "SELECT COUNT(*) as count FROM employees WHERE owner_id = ? AND status = 'working'",
            (owner_id,)
        ).fetchone()["count"]
    else:
        active_employees = conn.execute(
            "SELECT COUNT(*) as count FROM employees WHERE status = 'working'"
        ).fetchone()["count"]

    conn.close()

    # Format token burn
    if total_tokens > 1_000_000:
        token_str = f"{total_tokens / 1_000_000:.2f}M"
    elif total_tokens > 1_000:
        token_str = f"{total_tokens / 1_000:.1f}K"
    else:
        token_str = f"{total_tokens:,}"

    return {
        "stats": [
            {
                "title": "Token Burn",
                "value": token_str,
                "description": "Total model consumption",
                "trend": f"{total_calls} calls",
            },
            {
                "title": "Expenditure",
                "value": f"${total_cost:.4f}" if total_cost < 1 else f"${total_cost:.2f}",
                "description": "API costs (USD)",
                "trend": f"~${total_cost / max(total_calls, 1):.4f}/call" if total_calls > 0 else "$0/call",
            },
            {
                "title": "Total Uptime",
                "value": _format_duration(total_run_seconds),
                "description": "Completed task/sprint/team run time",
                "trend": f"{active_employees} active",
            }
        ]
    }


@router.get("/usage")
async def get_dashboard_usage(
    user=Depends(get_current_user),
):
    """Get per-employee usage breakdown: tokens, cost, and run time."""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    owner_id = str(user["id"])
    store = get_store()
    conn = get_db()

    # Per-employee token/cost data
    employees = store.get_usage_by_employee(owner_id)

    result = []
    for emp in employees:
        emp_id = emp["id"]
        total_tokens = emp["total_tokens"]
        total_cost = emp["total_cost"]
        total_calls = emp["total_calls"]

        # Compute run time from tasks, sprints, team runs
        run_seconds = _compute_employee_run_time(conn, emp_id)

        # Count completed work items
        task_count = conn.execute(
            "SELECT COUNT(*) as c FROM employee_tasks WHERE employee_id = ? AND status = 'done'",
            (emp_id,)
        ).fetchone()["c"]
        sprint_count = conn.execute(
            "SELECT COUNT(*) as c FROM sprint_runs WHERE employee_id = ? AND status IN ('done', 'completed')",
            (emp_id,)
        ).fetchone()["c"]
        team_count = conn.execute(
            "SELECT COUNT(*) as c FROM team_run_members WHERE employee_id = ? AND task_status = 'done'",
            (emp_id,)
        ).fetchone()["c"]

        # Format tokens
        if total_tokens > 1_000_000:
            token_str = f"{total_tokens / 1_000_000:.2f}M"
        elif total_tokens > 1_000:
            token_str = f"{total_tokens / 1_000:.1f}K"
        else:
            token_str = str(total_tokens)

        result.append({
            "employee_id": emp_id,
            "name": emp["name"],
            "role": emp["role"],
            "model": emp["model"],
            "avatar_url": emp["avatar_url"],
            # Token usage
            "input_tokens": emp["input_tokens"],
            "output_tokens": emp["output_tokens"],
            "total_tokens": total_tokens,
            "total_tokens_formatted": token_str,
            # Cost
            "total_cost": round(total_cost, 6),
            "total_cost_formatted": f"${total_cost:.4f}" if total_cost < 1 else f"${total_cost:.2f}",
            # Run time (from completed tasks/sprints/team runs)
            "total_run_seconds": run_seconds,
            "total_run_time_formatted": _format_duration(run_seconds),
            # Work item counts
            "total_calls": total_calls,
            "tasks_completed": task_count,
            "sprint_runs_completed": sprint_count,
            "team_runs_completed": team_count,
        })

    conn.close()
    return {"employees": result}


@router.get("/activity")
async def get_dashboard_activity(
    user=Depends(get_current_user),
):
    """Get real-time multi-source activity feed."""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    owner_id = str(user["id"])
    conn = get_db()
    activities = []

    # 1. Fetch Employee Activities
    if owner_id:
        emp_rows = conn.execute(
            """
            SELECT id, activity_type, message, timestamp, employee_id
            FROM employee_activity_log
            WHERE employee_id IN (SELECT id FROM employees WHERE owner_id = ?)
            ORDER BY timestamp DESC LIMIT 10
            """,
            (owner_id,)
        ).fetchall()
    else:
        emp_rows = conn.execute(
            "SELECT id, activity_type, message, timestamp, employee_id FROM employee_activity_log ORDER BY timestamp DESC LIMIT 10"
        ).fetchall()

    for r in emp_rows:
        activities.append({
            "id": f"emp_{r['id']}",
            "source": "Employee",
            "sourceType": "task",
            "message": r["message"],
            "time": r["timestamp"],
            "color": "slate"
        })

    # 2. Fetch Sprint Activities (Messages)
    try:
        sprint_rows = conn.execute(
            """
            SELECT m.id, m.content, m.created_at, m.task_id
            FROM task_messages m
            JOIN sprint_tasks t ON m.task_id = t.id
            ORDER BY m.created_at DESC LIMIT 10
            """
        ).fetchall()

        for r in sprint_rows:
            activities.append({
                "id": f"spr_{r['id']}",
                "source": "Sprint",
                "sourceType": "sprint",
                "message": r["content"],
                "time": r["created_at"],
                "color": "blue"
            })
    except Exception:
        pass

    # 3. Fetch Team Activities (Messages)
    try:
        if owner_id:
            team_rows = conn.execute(
                """
                SELECT m.id, m.content, m.created_at, m.sender_name
                FROM team_messages m
                JOIN teams t ON m.conversation_id = t.id OR m.owner_id = ?
                ORDER BY m.created_at DESC LIMIT 10
                """,
                (owner_id,)
            ).fetchall()
        else:
            team_rows = conn.execute(
                "SELECT id, content, created_at, sender_name FROM team_messages ORDER BY created_at DESC LIMIT 10"
            ).fetchall()

        for r in team_rows:
            activities.append({
                "id": f"team_{r['id']}",
                "source": "Team",
                "sourceType": "team",
                "message": f"[{r['sender_name']}] {r['content']}",
                "time": r["created_at"],
                "color": "purple"
            })
    except Exception:
        pass

    conn.close()

    # Sort by time descending
    activities.sort(key=lambda x: x["time"], reverse=True)

    # Format time to "Xm ago" strings
    now = datetime.now()

    formatted_activities = []
    for a in activities[:15]:
        try:
            dt = datetime.fromisoformat(a["time"])
            diff = now - dt
            minutes = int(diff.total_seconds() / 60)
            if minutes < 1:
                time_str = "just now"
            elif minutes < 60:
                time_str = f"{minutes}m ago"
            elif minutes < 1440:
                time_str = f"{minutes // 60}h ago"
            else:
                time_str = f"{minutes // 1440}d ago"
        except Exception:
            time_str = "recently"

        a["time"] = time_str
        formatted_activities.append(a)

    return {"activities": formatted_activities}
