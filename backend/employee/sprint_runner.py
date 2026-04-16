"""
SprintRunner — creates and executes sprint task runs.

A SprintRun is a single activation of a sprint task where:
  - The task has an assigned employee (via CurrentSprintPage dropdown)
  - That employee is spawned as a GenericEmployeeAgent instance
  - The agent runs with auto_approve_human=True (no HITL pauses)
  - The agent is told which sprint session it belongs to so it can
    reference that session in its work and outputs
  - Progress + final output is persisted as task_messages on the task,
    visible in the activity log on the frontend

Usage:
    runner = SprintRunner(sprint_id, owner_id)
    run_id = await runner.start(task_id, user_id)
"""

import asyncio
import logging
from typing import Optional

from backend.store.sprint_store import SprintStore, generate_id
from backend.store.employee_store import EmployeeStore

logger = logging.getLogger("sprint_runner")


class SprintRunner:
    """Orchestrates the execution of a single sprint task."""

    def __init__(self, sprint_id: str, owner_id: str = ""):
        self.sprint_id = sprint_id
        self.owner_id = owner_id
        self.sprint_store = SprintStore()
        self.employee_store = EmployeeStore()

    def _get_employee(self, employee_id: str):
        emp = self.employee_store.get_employee(employee_id, self.owner_id)
        if not emp and self.owner_id:
            emp = self.employee_store.get_employee(employee_id, "")
        return emp

    async def start(self, task_id: str, user_id: str = "anonymous") -> str:
        """Create a sprint run session for a task and spawn the assigned employee.

        Returns the run_id (also used as the session id).
        """
        sprint = self.sprint_store.get_sprint(self.sprint_id)
        if not sprint:
            raise ValueError(f"Sprint {self.sprint_id} not found")

        tasks = self.sprint_store.get_sprint_tasks(self.sprint_id)
        task = next((t for t in tasks if t["id"] == task_id), None)
        if not task:
            raise ValueError(f"Task {task_id} not found in sprint {self.sprint_id}")

        employee_id = (task.get("employee_id") or "").strip()
        if not employee_id:
            raise ValueError(f"Task {task_id} has no assigned employee")

        emp = self._get_employee(employee_id)
        if not emp:
            raise ValueError(f"Employee {employee_id} not found")

        # Each sprint run gets its own session id so the agent can reference
        # which run it is executing the task in.
        run_id = generate_id("sprun")

        logger.info(
            "SprintRun %s created for sprint=%s task=%s employee=%s (%s)",
            run_id, self.sprint_id, task_id, emp.name, employee_id,
        )

        self.sprint_store.create_run(
            run_id=run_id,
            task_id=task_id,
            employee_id=employee_id,
            employee_name=emp.name,
        )

        # Post a system message to the task thread so the activity log shows
        # the run starting.
        self.sprint_store.add_task_message(
            task_id=task_id,
            content=f"[Sprint Run {run_id}] {emp.name} started task.",
            sender_id=employee_id,
            sender_name=emp.name,
            sender_type="system",
            message_type="system",
            run_id=run_id,
        )

        asyncio.create_task(
            self._run_task(
                run_id=run_id,
                sprint=sprint,
                task=task,
                employee=emp,
                user_id=user_id,
            ),
            name=f"sprint_run_{run_id}",
        )

        return run_id

    async def _run_task(self, run_id, sprint, task, employee, user_id) -> None:
        """Spawn the employee agent and stream its output into task messages."""
        from backend.employee.react_agent import GenericEmployeeAgent

        task_id = task["id"]
        employee_id = employee.id

        try:
            agent = GenericEmployeeAgent(
                employee_id=employee_id,
                user_id=user_id,
                owner_id=self.owner_id,
                run_id=run_id,
                user_context={
                    "sprint_run": True,
                    "run_id": run_id,
                    "sprint_id": self.sprint_id,
                    "sprint_name": sprint.get("name", ""),
                    "sprint_goal": sprint.get("goal", ""),
                    "task_id": task_id,
                    "task_title": task.get("title", ""),
                },
            )

            opening_prompt = self._build_opening_prompt(run_id, sprint, task)

            final_result = ""
            async for event in agent.chat(
                opening_prompt,
                stream=True,
                emit_events=True,
                auto_approve_human=True,
            ):
                if not isinstance(event, dict):
                    continue
                etype = event.get("type")
                if etype == "final":
                    final_result = event.get("content") or event.get("message") or ""
                    continue

                # Mirror the agent's own `manage_tasks` events into the run steps
                # table so the frontend can render them as a live checklist.
                if etype == "tool_result" and event.get("tool") == "manage_tasks":
                    self._apply_manage_tasks_event(run_id, event)
                    continue

                # Drop all other raw tool-call events — no more `🔧 Calling ...`
                # spam in the activity log. Steps already represent progress.
                if etype in ("tool_start", "tool_result", "plan_created"):
                    continue

                step_content = self._format_step_event(event)
                if not step_content:
                    continue
                try:
                    self.sprint_store.add_task_message(
                        task_id=task_id,
                        content=step_content[:4000],
                        sender_id=employee_id,
                        sender_name=employee.name,
                        sender_type="employee",
                        message_type=f"step_{etype}",
                        run_id=run_id,
                    )
                except Exception as e:
                    logger.debug("[SprintRun %s] failed to persist step: %s", run_id, e)

            stored_result = (final_result or "").strip() or "Task completed."

            self.sprint_store.add_task_message(
                task_id=task_id,
                content=stored_result[:8000],
                sender_id=employee_id,
                sender_name=employee.name,
                sender_type="employee",
                message_type="result",
                run_id=run_id,
            )
            self.sprint_store.update_run_status(run_id, "done", summary=stored_result[:4000])

            logger.info(
                "[SprintRun %s] %s (%s) finished task %s.",
                run_id, employee.name, employee_id, task_id,
            )

        except Exception as e:
            logger.exception(
                "[SprintRun %s] %s (%s) failed: %s",
                run_id, employee.name, employee_id, e,
            )
            self.sprint_store.add_task_message(
                task_id=task_id,
                content=f"[Sprint Run {run_id}] Failed: {str(e)[:500]}",
                sender_id=employee_id,
                sender_name=employee.name,
                sender_type="system",
                message_type="error",
                run_id=run_id,
            )
            self.sprint_store.update_run_status(run_id, "failed", error=str(e)[:500])

    def _apply_manage_tasks_event(self, run_id: str, event: dict) -> None:
        """Translate a `manage_tasks` tool_result into run_step upserts.

        All data comes from the agent's own plan — nothing tool-name-specific
        or hardcoded. Whatever the LLM put in `create_plan` is what shows up.
        """
        inp = event.get("input") or {}
        data = event.get("data") or {}
        action = inp.get("action")
        if not event.get("success", True):
            return

        if action == "create_plan" and isinstance(data, dict):
            tasks_list = data.get("tasks") or []
            for idx, t in enumerate(tasks_list, start=1):
                step_id = t.get("task_id") or ""
                title = t.get("title") or ""
                status = t.get("status") or "todo"
                if step_id:
                    self.sprint_store.upsert_run_step(
                        step_id=step_id,
                        run_id=run_id,
                        title=title,
                        status=status,
                        order_index=idx,
                    )
            return

        if action in ("start_task", "complete_task", "block_task", "cancel_task"):
            status_map = {
                "start_task": "in_progress",
                "complete_task": "done",
                "block_task": "blocked",
                "cancel_task": "cancelled",
            }
            step_id = inp.get("task_id") or ""
            title = (data or {}).get("title") or ""
            if step_id:
                self.sprint_store.upsert_run_step(
                    step_id=step_id,
                    run_id=run_id,
                    title=title,
                    status=status_map[action],
                )
            return

        if action == "create_task" and isinstance(data, dict):
            step_id = data.get("task_id") or ""
            title = data.get("title") or ""
            if step_id:
                self.sprint_store.upsert_run_step(
                    step_id=step_id,
                    run_id=run_id,
                    title=title,
                    status=data.get("status") or "todo",
                )

    def _format_step_event(self, event: dict) -> str:
        """Turn a react-agent stream event into a short human-readable line."""
        etype = event.get("type") or ""
        if etype == "thinking":
            txt = (event.get("content") or event.get("message") or "").strip()
            if not txt:
                return ""
            return f"💭 {txt}"
        if etype == "tool_start":
            name = event.get("tool") or event.get("name") or "tool"
            args = event.get("args") or event.get("input") or ""
            if isinstance(args, (dict, list)):
                import json
                try:
                    args = json.dumps(args)[:300]
                except Exception:
                    args = str(args)[:300]
            else:
                args = str(args)[:300]
            return f"🔧 Calling {name}({args})"
        if etype == "tool_result":
            name = event.get("tool") or event.get("name") or "tool"
            result = event.get("result") or event.get("output") or ""
            if isinstance(result, (dict, list)):
                import json
                try:
                    result = json.dumps(result)[:500]
                except Exception:
                    result = str(result)[:500]
            else:
                result = str(result)[:500]
            return f"✓ {name} → {result}"
        if etype == "content":
            txt = (event.get("content") or "").strip()
            return txt if txt else ""
        return ""

    def _build_opening_prompt(self, run_id: str, sprint: dict, task: dict) -> str:
        sprint_name = sprint.get("name") or "Sprint"
        sprint_goal = sprint.get("goal") or ""
        title = task.get("title") or ""
        description = (task.get("description") or "").strip()
        requirements = (task.get("requirements") or "").strip()
        priority = task.get("priority") or "medium"

        desc_section = f"\n\nDescription:\n{description}" if description else ""
        req_section = f"\n\nRequirements:\n{requirements}" if requirements else ""
        goal_section = f"\n\nSprint Goal: {sprint_goal}" if sprint_goal else ""

        return (
            f"You are now executing a task as part of an active sprint session "
            f"(sprint_run_id = {run_id}).\n\n"
            f"Sprint: {sprint_name}{goal_section}\n\n"
            f"Task: {title}\n"
            f"Priority: {priority}"
            f"{desc_section}"
            f"{req_section}\n\n"
            f"SESSION CONTEXT: This is an autonomous sprint run. There is no human "
            f"available to answer follow-up questions mid-run — do NOT call ask_user "
            f"or block on human input. Make reasonable assumptions, proceed, and note "
            f"any assumptions in your FINAL SUMMARY.\n\n"
            f"When referring to this work in tool calls or outputs, use the sprint "
            f"run id '{run_id}' so it can be tracked back to this session.\n\n"
            f"START HERE:\n"
            f"1. Read the task description and requirements carefully.\n"
            f"2. Use your available tools to accomplish the task end-to-end.\n"
            f"3. When done, produce a detailed FINAL SUMMARY covering what you "
            f"accomplished, any assumptions you made, and anything a reviewer needs "
            f"to know to verify the work."
        )
