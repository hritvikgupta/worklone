"""
Workflow Notifications — notifies the employee who created a workflow
when execution state changes (paused, failed, completed, resumed).
"""

from datetime import datetime
from backend.db.stores.employee_store import EmployeeStore
from backend.db.stores.workflow_store import WorkflowStore
from backend.core.agents.employee.types import EmployeeActivity, ActivityType
from backend.core.workflows.utils import generate_id
from backend.core.logging import get_logger

logger = get_logger("notifications")

_employee_store = None


def _get_employee_store() -> EmployeeStore:
    global _employee_store
    if _employee_store is None:
        _employee_store = EmployeeStore()
    return _employee_store


def notify_workflow_event(
    workflow_id: str,
    workflow_name: str,
    event: str,
    created_by_actor_id: str = "",
    created_by_actor_type: str = "",
    message: str = "",
    metadata: dict = None,
) -> None:
    """
    Log an activity to the employee who created the workflow.

    event: "paused", "failed", "completed", "resumed"
    """
    if created_by_actor_type != "employee" or not created_by_actor_id:
        logger.debug(f"Skipping notification — creator is not an employee: {created_by_actor_type}/{created_by_actor_id}")
        return

    event_map = {
        "paused": ActivityType.WORKFLOW_PAUSED,
        "failed": ActivityType.WORKFLOW_FAILED,
        "completed": ActivityType.WORKFLOW_COMPLETED,
        "resumed": ActivityType.WORKFLOW_RESUMED,
    }

    activity_type = event_map.get(event)
    if not activity_type:
        logger.warning(f"Unknown workflow event: {event}")
        return

    store = _get_employee_store()
    activity = EmployeeActivity(
        id=generate_id("act"),
        employee_id=created_by_actor_id,
        activity_type=activity_type,
        message=message or f"Workflow '{workflow_name}' {event}",
        metadata={
            "workflow_id": workflow_id,
            "workflow_name": workflow_name,
            "event": event,
            **(metadata or {}),
        },
        timestamp=datetime.now(),
    )

    try:
        store.log_activity(activity)
        logger.info(f"Notified employee {created_by_actor_id}: workflow '{workflow_name}' {event}")
    except Exception as e:
        logger.exception(f"Failed to notify employee {created_by_actor_id}: {e}")


def notify_from_workflow(store: WorkflowStore, workflow_id: str, event: str, message: str = "", metadata: dict = None) -> None:
    """
    Convenience: load workflow metadata from DB and notify.
    """
    workflow = store.get_workflow(workflow_id)
    if not workflow:
        return

    notify_workflow_event(
        workflow_id=workflow_id,
        workflow_name=workflow.name,
        event=event,
        created_by_actor_id=workflow.created_by_actor_id,
        created_by_actor_type=workflow.created_by_actor_type,
        message=message,
        metadata=metadata,
    )
