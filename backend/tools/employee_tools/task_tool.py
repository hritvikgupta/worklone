"""
TaskTool — lets employees create, update, list, and manage their own tasks.

Like Claude's TaskCreate/TaskUpdate pattern: the employee plans work as tasks,
shows the plan to the user, then executes step by step.
"""

import json
from datetime import datetime
from uuid import uuid4

from backend.tools.system_tools.base import BaseTool, ToolResult
from backend.store.employee_store import EmployeeStore
from backend.employee.types import EmployeeTask, TaskStatus, TaskPriority, ActivityType, EmployeeActivity


class TaskTool(BaseTool):
    name = "manage_tasks"
    description = (
        "Create, update, list, and manage your own tasks. Use this to plan work, "
        "track progress, and show your task plan to the user before executing."
    )
    category = "employee"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "create_task",
                        "update_task",
                        "list_tasks",
                        "complete_task",
                        "start_task",
                        "block_task",
                        "cancel_task",
                        "delete_task",
                        "create_plan",
                    ],
                    "description": "Action to perform",
                },
                "task_id": {
                    "type": "string",
                    "description": "Task ID (for update/complete/start/block/cancel/delete)",
                },
                "title": {
                    "type": "string",
                    "description": "Task title (for create_task)",
                },
                "description": {
                    "type": "string",
                    "description": "Task description (for create_task/update_task)",
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "critical"],
                    "description": "Task priority",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags for the task",
                },
                "status_filter": {
                    "type": "string",
                    "enum": ["todo", "in_progress", "done", "blocked", "cancelled", "all"],
                    "description": "Filter tasks by status (for list_tasks)",
                },
                "tasks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "description": {"type": "string"},
                            "priority": {"type": "string"},
                        },
                        "required": ["title"],
                    },
                    "description": "List of tasks to create (for create_plan)",
                },
                "metadata": {
                    "type": "object",
                    "description": "Arbitrary metadata to attach",
                },
            },
            "required": ["action"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        action = parameters.get("action")
        ctx = context or {}
        employee_id = ctx.get("employee_id", "")
        if not employee_id:
            return ToolResult(False, "", error="No employee_id in context")

        store = EmployeeStore()

        if action == "create_task":
            return self._create_task(store, employee_id, parameters)

        if action == "create_plan":
            return self._create_plan(store, employee_id, parameters)

        if action == "list_tasks":
            return self._list_tasks(store, employee_id, parameters)

        if action == "update_task":
            return self._update_task(store, employee_id, parameters)

        if action == "start_task":
            return self._change_status(store, employee_id, parameters.get("task_id", ""), TaskStatus.IN_PROGRESS)

        if action == "complete_task":
            return self._change_status(store, employee_id, parameters.get("task_id", ""), TaskStatus.DONE)

        if action == "block_task":
            return self._change_status(store, employee_id, parameters.get("task_id", ""), TaskStatus.BLOCKED)

        if action == "cancel_task":
            return self._change_status(store, employee_id, parameters.get("task_id", ""), TaskStatus.CANCELLED)

        if action == "delete_task":
            task_id = parameters.get("task_id", "")
            deleted = store.delete_task(employee_id, task_id)
            if deleted:
                return ToolResult(True, f"Deleted task {task_id}")
            return ToolResult(False, "", error=f"Task not found: {task_id}")

        return ToolResult(False, "", error=f"Unknown action: {action}")

    def _create_task(self, store, employee_id, params) -> ToolResult:
        task = EmployeeTask(
            id=f"task_{uuid4().hex[:12]}",
            employee_id=employee_id,
            task_title=params.get("title", "Untitled task"),
            task_description=params.get("description", ""),
            status=TaskStatus.TODO,
            priority=TaskPriority(params.get("priority", "medium")),
            tags=params.get("tags", []),
            metadata=params.get("metadata", {}),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        store.create_task(task)
        self._log_activity(store, employee_id, task.id, f"Created task: {task.task_title}")
        return ToolResult(
            True,
            f"Created task {task.id}: {task.task_title}",
            data={
                "task_id": task.id,
                "title": task.task_title,
                "description": task.task_description,
                "status": "todo",
                "priority": task.priority.value,
            },
        )

    def _create_plan(self, store, employee_id, params) -> ToolResult:
        tasks_data = params.get("tasks", [])
        if not tasks_data:
            return ToolResult(False, "", error="No tasks provided for plan")

        created = []
        for i, t in enumerate(tasks_data):
            task = EmployeeTask(
                id=f"task_{uuid4().hex[:12]}",
                employee_id=employee_id,
                task_title=t.get("title", f"Step {i + 1}"),
                task_description=t.get("description", ""),
                status=TaskStatus.TODO,
                priority=TaskPriority(t.get("priority", "medium")),
                tags=t.get("tags", []),
                metadata={"plan_order": i + 1},
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            store.create_task(task)
            created.append({
                "task_id": task.id,
                "order": i + 1,
                "title": task.task_title,
                "description": task.task_description,
                "status": task.status.value,
                "priority": task.priority.value,
            })

        plan_summary = "\n".join(f"  {c['order']}. [{c['task_id']}] {c['title']}" for c in created)
        self._log_activity(store, employee_id, "", f"Created plan with {len(created)} tasks")
        return ToolResult(
            True,
            f"Created plan with {len(created)} tasks:\n{plan_summary}",
            data={"tasks": created, "count": len(created)},
        )

    def _list_tasks(self, store, employee_id, params) -> ToolResult:
        tasks = store.get_employee_tasks(employee_id)
        status_filter = params.get("status_filter", "all")

        if status_filter != "all":
            tasks = [t for t in tasks if t.status.value == status_filter]

        if not tasks:
            return ToolResult(True, "No tasks found.", data={"tasks": [], "count": 0})

        lines = []
        for t in tasks:
            status_icon = {"todo": "○", "in_progress": "◑", "done": "●", "blocked": "✕", "cancelled": "—"}.get(t.status.value, "?")
            lines.append(f"  {status_icon} [{t.id}] {t.task_title} ({t.status.value}, {t.priority.value})")

        summary = "\n".join(lines)
        return ToolResult(
            True,
            f"{len(tasks)} task(s):\n{summary}",
            data={
                "tasks": [
                    {"task_id": t.id, "title": t.task_title, "status": t.status.value, "priority": t.priority.value}
                    for t in tasks
                ],
                "count": len(tasks),
            },
        )

    def _update_task(self, store, employee_id, params) -> ToolResult:
        task_id = params.get("task_id", "")
        if not task_id:
            return ToolResult(False, "", error="task_id is required")

        updates = {}
        if "title" in params:
            updates["task_title"] = params["title"]
        if "description" in params:
            updates["task_description"] = params["description"]
        if "priority" in params:
            updates["priority"] = params["priority"]
        if "tags" in params:
            updates["tags"] = params["tags"]
        if "metadata" in params:
            updates["metadata"] = params["metadata"]

        if not updates:
            return ToolResult(False, "", error="No fields to update")

        updated = store.update_task(employee_id, task_id, updates)
        if updated:
            return ToolResult(True, f"Updated task {task_id}", data={"task_id": task_id})
        return ToolResult(False, "", error=f"Task not found: {task_id}")

    def _change_status(self, store, employee_id, task_id, new_status: TaskStatus) -> ToolResult:
        if not task_id:
            return ToolResult(False, "", error="task_id is required")

        updates = {"status": new_status.value}
        if new_status == TaskStatus.DONE:
            updates["metadata"] = json.dumps({"completed_at": datetime.now().isoformat()})

        updated = store.update_task(employee_id, task_id, updates)
        if updated:
            self._log_activity(
                store,
                employee_id,
                task_id,
                f"{updated.task_title} → {new_status.value.replace('_', ' ')}",
            )
            return ToolResult(
                True,
                f"{updated.task_title} → {new_status.value}",
                data={
                    "task_id": task_id,
                    "title": updated.task_title,
                    "status": new_status.value,
                },
            )
        return ToolResult(False, "", error=f"Task not found: {task_id}")

    def _log_activity(self, store, employee_id, task_id, message):
        try:
            store.log_activity(EmployeeActivity(
                id=f"act_{uuid4().hex[:12]}",
                employee_id=employee_id,
                activity_type=ActivityType.WORK_STARTED if "Created" in message else ActivityType.TASK_COMPLETED,
                message=message,
                task_id=task_id,
                timestamp=datetime.now(),
            ))
        except Exception:
            pass
