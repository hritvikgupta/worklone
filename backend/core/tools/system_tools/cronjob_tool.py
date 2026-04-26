"""Cronjob Tool — manage recurring jobs using native workflow scheduler."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from backend.core.tools.run_tools.llm_tool import LLMTool
from backend.core.tools.system_tools.base import BaseTool, ToolResult
from backend.core.workflows.schedules.normalize import next_run_from_cron
from backend.core.workflows.types import WorkflowStatus, WorkflowTask, WorkflowTaskStatus
from backend.core.workflows.utils import generate_id
from backend.db.stores.workflow_store import WorkflowStore
from backend.services.llm_config import get_user_provider_config


CRONJOB_MARKER = "employee_cronjob_v1"


class CronjobTool(BaseTool):
    """Create/list/update/pause/resume/remove/run scheduled jobs."""

    name = "cronjob"
    description = (
        "Manage recurring cron jobs for this user. "
        "Actions: create, list, update, pause, resume, remove, run."
    )
    category = "core"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["create", "list", "update", "pause", "resume", "remove", "run"],
                    "description": "Cronjob action",
                },
                "job_id": {
                    "type": "string",
                    "description": "Required for update/pause/resume/remove/run",
                },
                "name": {
                    "type": "string",
                    "description": "Job display name",
                },
                "prompt": {
                    "type": "string",
                    "description": "Task prompt/description to execute each run",
                },
                "schedule": {
                    "type": "string",
                    "description": "Cron expression, e.g. '0 9 * * *'",
                },
                "timezone": {
                    "type": "string",
                    "description": "Timezone (default UTC)",
                },
                "limit": {
                    "type": "integer",
                    "description": "List limit (1-50), default 20",
                },
            },
            "required": ["action"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        ctx = context or {}
        owner_id = (ctx.get("owner_id") or ctx.get("user_id") or "").strip()
        if not owner_id:
            return ToolResult(False, "", error="No user context found for cronjob tool.")

        action = (parameters.get("action") or "").strip().lower()
        store = WorkflowStore()

        if action == "create":
            return await self._create(store, owner_id, parameters, ctx)
        if action == "list":
            return self._list(store, owner_id, parameters)
        if action == "update":
            return await self._update(store, owner_id, parameters)
        if action == "pause":
            return self._pause_resume(store, owner_id, parameters, pause=True)
        if action == "resume":
            return self._pause_resume(store, owner_id, parameters, pause=False)
        if action == "remove":
            return self._remove(store, owner_id, parameters)
        if action == "run":
            return await self._run_now(store, owner_id, parameters)

        return ToolResult(False, "", error=f"Unknown action '{action}'.")

    async def _create(self, store: WorkflowStore, owner_id: str, params: dict, ctx: dict) -> ToolResult:
        name = (params.get("name") or "").strip() or "Scheduled job"
        prompt = (params.get("prompt") or "").strip()
        schedule = (params.get("schedule") or "").strip()
        timezone = (params.get("timezone") or "UTC").strip() or "UTC"

        if not prompt:
            return ToolResult(False, "", error="create requires 'prompt'.")
        if not schedule:
            return ToolResult(False, "", error="create requires 'schedule' (cron expression).")

        next_run = next_run_from_cron(schedule)
        if next_run is None:
            return ToolResult(False, "", error=f"Invalid or unsupported cron expression: '{schedule}'.")

        tasks = await self._decompose_prompt_to_tasks(prompt, owner_id=owner_id)
        allowed_tools = await self._infer_allowed_tools(prompt=prompt, tasks=tasks, owner_id=owner_id)
        if not allowed_tools:
            return ToolResult(
                False,
                "",
                error=(
                    "Couldn't determine a safe tool allowlist for this cron job. "
                    "Please make the prompt more specific about target systems/actions."
                ),
            )

        workflow_id = generate_id("wf")
        actor_type = (ctx.get("actor_type") or "employee").strip() or "employee"
        actor_id = (ctx.get("actor_id") or ctx.get("employee_id") or "employee").strip() or "employee"
        actor_name = (ctx.get("actor_name") or ctx.get("employee_name") or "Employee").strip() or "Employee"

        workflow = store.create_workflow(
            workflow_id=workflow_id,
            name=name,
            description=f"Cron job: {name}",
            user_id=owner_id,
            created_by_actor_type=actor_type,
            created_by_actor_id=actor_id,
            created_by_actor_name=actor_name,
            tasks=tasks,
            allowed_tools=allowed_tools,
        )
        store.add_trigger(
            workflow_id=workflow.id,
            trigger_id=generate_id("trig"),
            trigger_type="schedule",
            config={"cron": schedule, "timezone": timezone},
        )

        workflow = store.get_workflow(workflow.id, owner_id)
        if not workflow:
            return ToolResult(False, "", error="Created job but failed to reload workflow.")

        workflow.variables["system_tool"] = CRONJOB_MARKER
        workflow.variables["cronjob"] = {
            "schedule": schedule,
            "timezone": timezone,
            "prompt": prompt,
            "allowed_tools": allowed_tools,
            "created_at": datetime.now().isoformat(),
        }
        store.save_workflow(workflow)
        store.update_workflow_status(
            workflow.id,
            WorkflowStatus.ACTIVE.value,
            handoff_actor_type=actor_type,
            handoff_actor_id=actor_id,
            handoff_actor_name=actor_name,
        )

        return ToolResult(
            True,
            f"Created cron job '{name}' ({workflow.id}) schedule='{schedule}' next_run='{next_run.isoformat()}'.",
            data={
                "job_id": workflow.id,
                "name": name,
                "schedule": schedule,
                "timezone": timezone,
                "next_run_at": next_run.isoformat(),
            },
        )

    def _list(self, store: WorkflowStore, owner_id: str, params: dict) -> ToolResult:
        raw_limit = params.get("limit", 20)
        try:
            limit = max(1, min(50, int(raw_limit)))
        except Exception:
            limit = 20

        jobs = self._list_jobs(store, owner_id)[:limit]
        if not jobs:
            return ToolResult(True, "No cron jobs found.", data={"jobs": []})

        lines = [f"Cron jobs ({len(jobs)}):"]
        for i, job in enumerate(jobs, start=1):
            lines.append(
                f"{i}. {job['name']} (id={job['job_id']}, state={job['state']}, schedule={job['schedule']}, next={job['next_run_at']})"
            )
            if job.get("prompt"):
                prompt = job["prompt"].replace("\n", " ")
                if len(prompt) > 140:
                    prompt = prompt[:140] + "..."
                lines.append(f"   Prompt: {prompt}")

        return ToolResult(True, "\n".join(lines), data={"jobs": jobs})

    async def _update(self, store: WorkflowStore, owner_id: str, params: dict) -> ToolResult:
        workflow = self._get_job_or_error(store, owner_id, params.get("job_id"))
        if isinstance(workflow, ToolResult):
            return workflow

        changed = False
        if params.get("name") is not None:
            workflow.name = (params.get("name") or "").strip() or workflow.name
            changed = True

        cron_cfg = self._get_schedule_trigger(workflow)
        if isinstance(cron_cfg, ToolResult):
            return cron_cfg
        trigger = cron_cfg

        if params.get("schedule") is not None:
            schedule = (params.get("schedule") or "").strip()
            if not schedule:
                return ToolResult(False, "", error="schedule cannot be empty.")
            next_run = next_run_from_cron(schedule)
            if next_run is None:
                return ToolResult(False, "", error=f"Invalid or unsupported cron expression: '{schedule}'.")
            trigger.cron_expression = schedule
            trigger.config["cron"] = schedule
            trigger.next_run_at = next_run
            changed = True

        if params.get("timezone") is not None:
            timezone = (params.get("timezone") or "UTC").strip() or "UTC"
            trigger.timezone = timezone
            trigger.config["timezone"] = timezone
            changed = True

        if params.get("prompt") is not None:
            prompt = (params.get("prompt") or "").strip()
            if not prompt:
                return ToolResult(False, "", error="prompt cannot be empty.")
            if workflow.tasks:
                workflow.tasks[0].description = prompt
                workflow.tasks[0].status = WorkflowTaskStatus.PENDING
                workflow.tasks[0].result = ""
                workflow.tasks[0].error = ""
            else:
                workflow.tasks.append(
                    WorkflowTask(
                        id=generate_id("task"),
                        description=prompt,
                        status=WorkflowTaskStatus.PENDING,
                    )
                )
            workflow.variables.setdefault("cronjob", {})["prompt"] = prompt
            changed = True

        if not changed:
            return ToolResult(False, "", error="No updates provided.")

        if params.get("prompt") is not None:
            prompt_value = (params.get("prompt") or "").strip()
            tasks = [t.description for t in workflow.tasks] if workflow.tasks else [prompt_value]
            new_allowed_tools = await self._infer_allowed_tools(
                prompt=prompt_value,
                tasks=tasks,
                owner_id=owner_id,
            )
            if new_allowed_tools:
                workflow.allowed_tools = new_allowed_tools
                workflow.variables.setdefault("cronjob", {})["allowed_tools"] = new_allowed_tools
            else:
                return ToolResult(
                    False,
                    "",
                    error=(
                        "Prompt update would leave this cron job without a valid tool allowlist. "
                        "Please use a more specific prompt."
                    ),
                )

        workflow.updated_at = datetime.now()
        store.save_workflow(workflow)

        schedule = trigger.cron_expression or trigger.config.get("cron", "")
        next_run_at = trigger.next_run_at.isoformat() if trigger.next_run_at else ""
        return ToolResult(
            True,
            f"Updated cron job {workflow.id} (schedule='{schedule}', next='{next_run_at}').",
            data={
                "job_id": workflow.id,
                "name": workflow.name,
                "schedule": schedule,
                "next_run_at": next_run_at,
            },
        )

    def _pause_resume(self, store: WorkflowStore, owner_id: str, params: dict, pause: bool) -> ToolResult:
        workflow = self._get_job_or_error(store, owner_id, params.get("job_id"))
        if isinstance(workflow, ToolResult):
            return workflow

        trigger = self._get_schedule_trigger(workflow)
        if isinstance(trigger, ToolResult):
            return trigger

        if pause:
            trigger.enabled = False
            store.update_workflow_status(workflow.id, WorkflowStatus.PAUSED.value)
            state = "paused"
        else:
            trigger.enabled = True
            schedule = trigger.cron_expression or trigger.config.get("cron", "")
            if schedule:
                trigger.next_run_at = next_run_from_cron(schedule)
            store.update_workflow_status(workflow.id, WorkflowStatus.ACTIVE.value)
            state = "active"

        workflow.updated_at = datetime.now()
        store.save_workflow(workflow)

        return ToolResult(
            True,
            f"Cron job {workflow.id} is now {state}.",
            data={
                "job_id": workflow.id,
                "state": state,
                "next_run_at": trigger.next_run_at.isoformat() if trigger.next_run_at else None,
            },
        )

    def _remove(self, store: WorkflowStore, owner_id: str, params: dict) -> ToolResult:
        job_id = (params.get("job_id") or "").strip()
        if not job_id:
            return ToolResult(False, "", error="job_id is required for remove.")

        workflow = self._get_job_or_error(store, owner_id, job_id)
        if isinstance(workflow, ToolResult):
            return workflow

        deleted = store.delete_workflow(workflow.id, owner_id)
        if not deleted:
            return ToolResult(False, "", error=f"Failed to remove cron job '{workflow.id}'.")

        return ToolResult(
            True,
            f"Removed cron job {workflow.id} ({workflow.name}).",
            data={"job_id": workflow.id},
        )

    async def _run_now(self, store: WorkflowStore, owner_id: str, params: dict) -> ToolResult:
        workflow = self._get_job_or_error(store, owner_id, params.get("job_id"))
        if isinstance(workflow, ToolResult):
            return workflow

        from backend.core.workflows.engine.executor import WorkflowExecutor

        executor = WorkflowExecutor(store)
        result = await executor.execute_workflow(
            workflow_id=workflow.id,
            trigger_type="manual",
            owner_id=owner_id,
            is_background=True,
        )

        return ToolResult(
            True,
            f"Triggered cron job {workflow.id} now (execution_id={result.execution_id}).",
            data={
                "job_id": workflow.id,
                "execution_id": result.execution_id,
                "status": result.status.value,
            },
        )

    def _list_jobs(self, store: WorkflowStore, owner_id: str) -> list[dict[str, Any]]:
        workflows = store.list_workflows(owner_id)
        jobs: list[dict[str, Any]] = []

        for wf in workflows:
            if wf.variables.get("system_tool") != CRONJOB_MARKER:
                continue

            trigger = None
            for t in wf.triggers:
                if t.trigger_type.value == "schedule":
                    trigger = t
                    break
            if not trigger:
                continue

            prompt = wf.tasks[0].description if wf.tasks else wf.description
            jobs.append({
                "job_id": wf.id,
                "name": wf.name,
                "state": wf.status.value,
                "schedule": trigger.cron_expression or trigger.config.get("cron", ""),
                "timezone": trigger.timezone or trigger.config.get("timezone", "UTC"),
                "next_run_at": trigger.next_run_at.isoformat() if trigger.next_run_at else None,
                "prompt": prompt,
            })

        jobs.sort(key=lambda j: j.get("next_run_at") or "", reverse=False)
        return jobs

    def _get_job_or_error(self, store: WorkflowStore, owner_id: str, job_id: str | None):
        normalized = (job_id or "").strip()
        if not normalized:
            return ToolResult(False, "", error="job_id is required.")

        wf = store.get_workflow(normalized, owner_id)
        if not wf:
            return ToolResult(False, "", error=f"Cron job not found: {normalized}")
        if wf.variables.get("system_tool") != CRONJOB_MARKER:
            return ToolResult(False, "", error=f"Workflow {normalized} is not a cron job managed by this tool.")
        return wf

    def _get_schedule_trigger(self, workflow):
        for t in workflow.triggers:
            if t.trigger_type.value == "schedule":
                return t
        return ToolResult(False, "", error=f"Workflow {workflow.id} has no schedule trigger.")

    async def _decompose_prompt_to_tasks(self, prompt: str, owner_id: str = "") -> list[str]:
        """Split a natural-language prompt into sequential task steps via LLM.

        Mirrors the /workflows/generate architect so cron jobs run as
        proper step-by-step workflows instead of one bundled task. Falls
        back to a single-task list if decomposition fails.
        """
        import json as _json

        system_prompt = (
            "You are an expert workflow architect. Parse the user's request "
            "into a sequential list of natural language step descriptions. "
            "Return ONLY valid JSON of the form: "
            '{"tasks": ["Step 1 natural language description", "Step 2 natural language description", ...]} '
            "Keep each step concise and user-friendly (one action per step), 2-6 steps total. "
            "Do NOT mention specific tool names or implementation details."
        )

        try:
            llm_config = get_user_provider_config(owner_id, "openai/gpt-4o") if owner_id else None
            model = (llm_config or {}).get("model") or "openai/gpt-4o"
            response = await LLMTool().execute(
                {
                    "prompt": prompt,
                    "system_prompt": system_prompt,
                    "model": model,
                    "response_format": {"type": "json_object"},
                },
                context={"owner_id": owner_id} if owner_id else None,
            )
            if not response.success:
                return [prompt]

            content = (response.data or {}).get("content", "").strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]

            parsed = _json.loads(content.strip() or "{}")
            tasks = parsed.get("tasks") or []
            tasks = [str(t).strip() for t in tasks if str(t).strip()]
            return tasks if tasks else [prompt]
        except Exception:
            return [prompt]

    async def _infer_allowed_tools(self, prompt: str, tasks: list[str], owner_id: str = "") -> list[str]:
        """Infer minimal workflow tool allowlist from prompt/tasks using live catalog."""
        import json as _json
        from backend.core.tools.catalog import create_all_tools

        catalog_names = sorted({tool.name for tool in create_all_tools()})
        catalog_set = set(catalog_names)
        if not catalog_names:
            return []

        tasks_text = "\n".join(f"- {t}" for t in (tasks or []))
        system_prompt = (
            "You are selecting tools for a scheduled workflow. "
            "Return ONLY JSON of the form: {\"allowed_tools\": [\"tool_a\", \"tool_b\"]}. "
            "Pick the minimum necessary set. "
            "Use exact names from the provided catalog only. "
            "If uncertain, return an empty list."
        )
        user_prompt = (
            f"Workflow prompt:\n{prompt}\n\n"
            f"Workflow tasks:\n{tasks_text}\n\n"
            f"Tool catalog:\n{', '.join(catalog_names)}"
        )

        try:
            llm_config = get_user_provider_config(owner_id, "") if owner_id else None
            model = (llm_config or {}).get("model") or "openai/gpt-4o-mini"
            response = await LLMTool().execute(
                {
                    "prompt": user_prompt,
                    "system_prompt": system_prompt,
                    "model": model,
                    "response_format": {"type": "json_object"},
                },
                context={"owner_id": owner_id} if owner_id else None,
            )
            if not response.success:
                return []

            content = (response.data or {}).get("content", "").strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]

            parsed = _json.loads(content.strip() or "{}")
            requested = parsed.get("allowed_tools") or []
            if not isinstance(requested, list):
                return []

            cleaned = [str(t).strip() for t in requested if str(t).strip()]
            return [t for t in dict.fromkeys(cleaned) if t in catalog_set]
        except Exception:
            return []
