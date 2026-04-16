"""
TeamRunner — creates and executes team runs.

A TeamRun is a single activation of a team where:
  - Each member gets a specific task
  - Each member is spawned as a separate GenericEmployeeAgent instance
  - Agents run concurrently, discover context via get_my_team_context tool
  - All messages are threaded through one conversation_id
  - The human can observe (and optionally participate) via SSE events

Usage:
    runner = TeamRunner(team_id, owner_id)
    run_id = await runner.start(goal, member_tasks, user_id)
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Optional, AsyncGenerator

from backend.store.team_store import TeamStore
from backend.store.employee_store import EmployeeStore
from backend.employee.types import (
    TeamRun,
    TeamRunMember,
    TeamRunStatus,
    TeamMemberTaskStatus,
    TeamMessage,
    SenderType,
    MessageStatus,
)
from backend.workflows.utils import generate_id

logger = logging.getLogger("team_runner")


class TeamRunner:
    """Orchestrates the execution of a team run."""

    def __init__(self, team_id: str, owner_id: str):
        self.team_id = team_id
        self.owner_id = owner_id
        self.team_store = TeamStore()
        self.employee_store = EmployeeStore()

    def _get_employee(self, employee_id: str):
        """Get employee with owner_id scoping, falling back to unscoped for legacy rows."""
        emp = self.employee_store.get_employee(employee_id, self.owner_id)
        if not emp:
            emp = self.employee_store.get_employee(employee_id, "")
        return emp

    async def start(
        self,
        goal: str,
        member_tasks: dict[str, str],  # {employee_id: task_description}
        user_id: str = "anonymous",
        conversation_id: Optional[str] = None,
    ) -> str:
        """Create a TeamRun, assign tasks, and spawn all member agents.

        Returns the run_id.

        member_tasks example:
            {
                "emp_katy": "Review the job description and define requirements",
                "emp_sam": "Analyze the candidate pool and shortlist top 3",
                "emp_rachel": "Evaluate technical fit for each shortlisted candidate",
            }
        """
        # Validate team exists
        team = self.team_store.get_team(self.team_id, self.owner_id)
        if not team:
            raise ValueError(f"Team {self.team_id} not found")

        # Validate all employees exist (fallback to unscoped lookup for legacy rows)
        for emp_id in member_tasks:
            emp = self._get_employee(emp_id)
            if not emp:
                raise ValueError(f"Employee {emp_id} not found")

        conv_id = conversation_id or generate_id("conv")
        run_id = generate_id("run")
        now = datetime.now()

        # Create the run record
        run = TeamRun(
            id=run_id,
            team_id=self.team_id,
            owner_id=self.owner_id,
            conversation_id=conv_id,
            goal=goal,
            status=TeamRunStatus.RUNNING,
            created_at=now,
            updated_at=now,
        )
        self.team_store.create_run(run)

        # Create a run member record for each participant
        for emp_id, task in member_tasks.items():
            emp = self._get_employee(emp_id)
            member = TeamRunMember(
                id=generate_id("rm"),
                run_id=run_id,
                team_id=self.team_id,
                employee_id=emp_id,
                employee_name=emp.name if emp else emp_id,
                employee_role=emp.role if emp else "",
                assigned_task=task,
                task_status=TeamMemberTaskStatus.ASSIGNED,
                created_at=now,
                updated_at=now,
            )
            self.team_store.add_run_member(member)

        logger.info(
            "TeamRun %s created for team %s (%s topology) with %d members. goal=%s",
            run_id, self.team_id, team.topology.value, len(member_tasks), goal[:80]
        )

        # Spawn agents according to the team topology
        asyncio.create_task(
            self._execute_topology(
                run_id=run_id,
                team=team,
                member_tasks=member_tasks,
                goal=goal,
                conv_id=conv_id,
                user_id=user_id,
            ),
            name=f"topology_{run_id}",
        )

        return run_id

    async def _execute_topology(self, run_id, team, member_tasks, goal, conv_id, user_id):
        """Route execution to the correct topology handler."""
        from backend.employee.types import TeamTopology
        try:
            if team.topology == TeamTopology.SEQUENTIAL:
                await self._execute_sequential(run_id, team, member_tasks, goal, conv_id, user_id)
            elif team.topology == TeamTopology.BROADCAST:
                await self._execute_broadcast(run_id, team, member_tasks, goal, conv_id, user_id)
            else:
                # GRAPH (default) — all agents run concurrently, free to message each other
                await self._execute_graph(run_id, member_tasks, goal, conv_id, user_id)
        except Exception as e:
            logger.exception("Topology execution failed for run %s: %s", run_id, e)
            self.team_store.update_run_status(run_id, TeamRunStatus.FAILED)

    async def _execute_graph(self, run_id, member_tasks, goal, conv_id, user_id):
        """Graph topology — all agents spawn concurrently. Any agent can message any other."""
        agent_tasks = [
            asyncio.create_task(
                self._run_member(run_id=run_id, employee_id=emp_id, task=task,
                                 goal=goal, conv_id=conv_id, user_id=user_id,
                                 prior_context="", topology="graph"),
                name=f"team_run_{run_id}_{emp_id}",
            )
            for emp_id, task in member_tasks.items()
        ]
        await self._monitor_run(run_id, agent_tasks)

    async def _execute_sequential(self, run_id, team, member_tasks, goal, conv_id, user_id):
        """Sequential topology — agents run one at a time in sequenceOrder.
        Each agent receives the previous agent's result as context.
        """
        # Build ordered list using team.sequence_order, fallback to member_tasks key order
        ordered_ids = [
            eid for eid in (team.sequence_order or [])
            if eid in member_tasks
        ]
        # Append any member_tasks not in sequence_order
        for eid in member_tasks:
            if eid not in ordered_ids:
                ordered_ids.append(eid)

        prior_context = ""
        all_tasks = []

        for emp_id in ordered_ids:
            task = member_tasks[emp_id]
            emp = self._get_employee(emp_id)
            emp_name = emp.name if emp else emp_id

            logger.info("[Sequential] Starting %s (%s)", emp_name, emp_id)

            # Run this agent synchronously (await it before moving on)
            single_task = asyncio.create_task(
                self._run_member(
                    run_id=run_id,
                    employee_id=emp_id,
                    task=task,
                    goal=goal,
                    conv_id=conv_id,
                    user_id=user_id,
                    prior_context=prior_context,
                    topology="sequential",
                ),
                name=f"team_run_{run_id}_{emp_id}",
            )
            await single_task
            all_tasks.append(single_task)

            # Get this agent's result to pass as context to the next
            member = self.team_store.get_run_member(run_id, emp_id)
            if member and member.result and member.result != "Completed.":
                prior_context = f"Previous step ({emp_name}) full output:\n{member.result}"

        await self._monitor_run(run_id, all_tasks)

    async def _execute_broadcast(self, run_id, team, member_tasks, goal, conv_id, user_id):
        """Broadcast topology — broadcaster runs first, then all receivers run in parallel
        with the broadcaster's output injected as their starting context.
        """
        broadcaster_id = team.broadcaster_id
        if not broadcaster_id or broadcaster_id not in member_tasks:
            # Fall back to first member as broadcaster
            broadcaster_id = next(iter(member_tasks))

        receiver_ids = [eid for eid in member_tasks if eid != broadcaster_id]

        emp = self._get_employee(broadcaster_id)
        broadcaster_name = emp.name if emp else broadcaster_id
        logger.info("[Broadcast] Running broadcaster: %s", broadcaster_name)

        # Step 1: run broadcaster
        broadcast_task = asyncio.create_task(
            self._run_member(
                run_id=run_id,
                employee_id=broadcaster_id,
                task=member_tasks[broadcaster_id],
                goal=goal,
                conv_id=conv_id,
                user_id=user_id,
                prior_context="",
                topology="broadcast_sender",
            ),
            name=f"team_run_{run_id}_{broadcaster_id}",
        )
        await broadcast_task

        # Get broadcaster result
        broadcaster_member = self.team_store.get_run_member(run_id, broadcaster_id)
        broadcast_output = broadcaster_member.result if broadcaster_member else ""
        prior_context = f"{broadcaster_name} broadcast (full output):\n{broadcast_output}"

        logger.info("[Broadcast] Spawning %d receivers", len(receiver_ids))

        # Step 2: spawn all receivers in parallel with broadcaster's output
        receiver_tasks = [
            asyncio.create_task(
                self._run_member(
                    run_id=run_id,
                    employee_id=emp_id,
                    task=member_tasks[emp_id],
                    goal=goal,
                    conv_id=conv_id,
                    user_id=user_id,
                    prior_context=prior_context,
                    topology="broadcast_receiver",
                ),
                name=f"team_run_{run_id}_{emp_id}",
            )
            for emp_id in receiver_ids
        ]
        all_tasks = [broadcast_task] + receiver_tasks
        await self._monitor_run(run_id, receiver_tasks)

        # Final status check
        members = self.team_store.list_run_members(run_id)
        failed = any(m.task_status == TeamMemberTaskStatus.BLOCKED for m in members)
        self.team_store.update_run_status(
            run_id,
            TeamRunStatus.FAILED if failed else TeamRunStatus.COMPLETED
        )

    async def _run_member(
        self,
        run_id: str,
        employee_id: str,
        task: str,
        goal: str,
        conv_id: str,
        user_id: str,
        prior_context: str = "",
        topology: str = "graph",
    ) -> None:
        """Run a single team member's agent for this team run."""
        from backend.employee.react_agent import GenericEmployeeAgent

        self.team_store.update_run_member(
            run_id, employee_id, task_status=TeamMemberTaskStatus.IN_PROGRESS
        )

        emp = self._get_employee(employee_id)
        emp_name = emp.name if emp else employee_id

        try:
            agent = GenericEmployeeAgent(
                employee_id=employee_id,
                user_id=user_id,
                owner_id=self.owner_id,
                team_id=self.team_id,
                run_id=run_id,
                user_context={
                    "team_run": True,
                    "run_id": run_id,
                    "team_id": self.team_id,
                    "conversation_id": conv_id,
                    "goal": goal,
                },
            )

            # Opening prompt: agent is told its task, instructed to use get_my_team_context first
            prior_section = f"\n\nContext from previous step:\n{prior_context}" if prior_context else ""

            # Topology-specific coordination rules so agents don't deadlock waiting
            # for teammates that haven't spawned yet or have already finished.
            if topology == "sequential":
                coord_rules = (
                    "TOPOLOGY: SEQUENTIAL. Teammates listed before you have already finished — they "
                    "cannot respond. Teammates listed after you have NOT started yet — they cannot "
                    "respond either. DO NOT call send_message_to_coworker with wait_for_reply=true. "
                    "Put everything the next agent needs directly into your FINAL SUMMARY at the end "
                    "of this run — that summary is automatically handed to the next agent as context."
                )
            elif topology == "broadcast_sender":
                coord_rules = (
                    "TOPOLOGY: BROADCAST (you are the broadcaster). Receivers have NOT started yet — "
                    "do not wait_for_reply. Put everything they need into your FINAL SUMMARY; it will "
                    "be handed to every receiver as their starting context."
                )
            elif topology == "broadcast_receiver":
                coord_rules = (
                    "TOPOLOGY: BROADCAST (you are a receiver). The broadcaster is done and other "
                    "receivers run in parallel with you. Only wait_for_reply on teammates you can see "
                    "are currently running (task_status=in_progress in get_my_team_context)."
                )
            else:
                coord_rules = (
                    "TOPOLOGY: GRAPH. All teammates run concurrently. You may use "
                    "send_message_to_coworker with wait_for_reply=true only when you truly need a "
                    "response to proceed."
                )

            opening_prompt = (
                f"You are now part of an active team session (run_id = {run_id}).\n\n"
                f"Team Goal: {goal}\n\n"
                f"Your Task: {task}"
                f"{prior_section}\n\n"
                f"{coord_rules}\n\n"
                f"TEAM SESSION MEMORY: This team run has a SHARED scratchpad visible to every "
                f"teammate in the same session. Use it as the team's working memory:\n"
                f"  • team_memory_read()               → see everything teammates have stored\n"
                f"  • team_memory_read(key='...')      → fetch one specific entry in full\n"
                f"  • team_memory_write(key, value)    → save a finding/artifact for teammates\n"
                f"Anything you put in team_memory_write persists for the whole session and is "
                f"visible to every agent in this run. When the team runs again later, previous "
                f"session summaries will be surfaced automatically via get_my_team_context.\n\n"
                f"START HERE:\n"
                f"1. Call get_my_team_context FIRST. It returns the goal, teammates, the current "
                f"   scratchpad, the conversation thread, and summaries of previous sessions.\n"
                f"2. Read any relevant scratchpad entries before re-deriving work teammates have "
                f"   already done.\n"
                f"3. Do your task. Save important intermediate artifacts to team_memory_write so "
                f"   downstream agents don't have to reconstruct them.\n"
                f"4. When done, produce a detailed FINAL SUMMARY (what you accomplished, key "
                f"   findings, and anything the next agent or next run needs to know)."
            )

            final_result = ""
            async for event in agent.chat(opening_prompt, stream=True, emit_events=True, auto_approve_human=True):
                if isinstance(event, dict):
                    if event.get("type") == "final":
                        # react_agent emits {"type": "final", "content": ...}
                        final_result = event.get("content") or event.get("message") or ""
                    elif event.get("type") in ("thinking", "tool_start", "tool_result"):
                        # Log team run events for observability
                        logger.debug(
                            "[TeamRun %s] [%s] %s: %s",
                            run_id, emp_name, event.get("type"),
                            str(event)[:200],
                        )

            # Save the final result back to the run member record.
            # Cap is generous so downstream agents see the full handoff, not a stub.
            stored_result = (final_result or "").strip()
            self.team_store.update_run_member(
                run_id, employee_id,
                task_status=TeamMemberTaskStatus.DONE,
                result=stored_result[:8000] if stored_result else "Completed.",
            )

            # Post the result as a message in the team conversation for all to see
            self.team_store.send_message(TeamMessage(
                id=generate_id("msg"),
                conversation_id=conv_id,
                sender_type=SenderType.EMPLOYEE,
                sender_id=employee_id,
                sender_name=emp_name,
                content=f"[Task Complete] {stored_result[:4000] if stored_result else 'Task completed.'}",
                recipient_type=SenderType.HUMAN,
                recipient_id=user_id,
                recipient_name="Team",
                status=MessageStatus.PENDING,
                owner_id=self.owner_id,
            ))

            logger.info(
                "[TeamRun %s] %s (%s) finished task.",
                run_id, emp_name, employee_id,
            )

        except Exception as e:
            logger.exception(
                "[TeamRun %s] %s (%s) failed: %s", run_id, emp_name, employee_id, e
            )
            self.team_store.update_run_member(
                run_id, employee_id,
                task_status=TeamMemberTaskStatus.BLOCKED,
                result=f"Failed: {str(e)[:500]}",
            )

    async def _monitor_run(self, run_id: str, agent_tasks: list) -> None:
        """Wait for all member tasks to complete then mark the run done."""
        try:
            await asyncio.gather(*agent_tasks, return_exceptions=True)

            # Check if any member failed
            members = self.team_store.list_run_members(run_id)
            failed = any(m.task_status == TeamMemberTaskStatus.BLOCKED for m in members)

            final_status = TeamRunStatus.FAILED if failed else TeamRunStatus.COMPLETED
            self.team_store.update_run_status(run_id, final_status)

            logger.info(
                "[TeamRun %s] All members finished. Status: %s",
                run_id, final_status.value,
            )
        except Exception as e:
            logger.exception("[TeamRun %s] Monitor failed: %s", run_id, e)
            self.team_store.update_run_status(run_id, TeamRunStatus.FAILED)

    async def stream_run_events(self, run_id: str) -> AsyncGenerator[dict, None]:
        """Stream run progress by polling the DB — for SSE endpoint use.

        Yields dicts representing run state changes and member status updates.
        Polls every 2 seconds until the run completes or fails.
        """
        seen_statuses: dict[str, str] = {}
        max_polls = 300  # 10 minutes max

        for _ in range(max_polls):
            full = self.team_store.get_full_run(run_id)
            if not full:
                yield {"type": "error", "message": f"Run {run_id} not found"}
                return

            run = full["run"]
            members = full["members"]

            # Emit status changes for each member
            for m in members:
                prev = seen_statuses.get(m.employee_id)
                if prev != m.task_status.value:
                    seen_statuses[m.employee_id] = m.task_status.value
                    yield {
                        "type": "member_status",
                        "run_id": run_id,
                        "employee_id": m.employee_id,
                        "employee_name": m.employee_name,
                        "task_status": m.task_status.value,
                        "result": m.result if m.task_status == TeamMemberTaskStatus.DONE else "",
                    }

            # Check run completion
            if run.status in (TeamRunStatus.COMPLETED, TeamRunStatus.FAILED):
                yield {
                    "type": "run_complete",
                    "run_id": run_id,
                    "status": run.status.value,
                    "members": [
                        {
                            "employee_id": m.employee_id,
                            "employee_name": m.employee_name,
                            "task_status": m.task_status.value,
                            "result": m.result,
                        }
                        for m in members
                    ],
                }
                return

            await asyncio.sleep(2)

        yield {"type": "timeout", "run_id": run_id, "message": "Stream timed out"}
