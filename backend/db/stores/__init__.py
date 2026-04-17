"""Concrete persistence stores backed by the shared application database."""

__all__ = [
    "AuthDB",
    "EmployeeStore",
    "FileStore",
    "SprintStore",
    "TeamStore",
    "WorkflowStore",
]


def __getattr__(name: str):
    if name == "AuthDB":
        from backend.db.stores.auth_store import AuthDB

        return AuthDB
    if name == "EmployeeStore":
        from backend.db.stores.employee_store import EmployeeStore

        return EmployeeStore
    if name == "FileStore":
        from backend.db.stores.file_store import FileStore

        return FileStore
    if name == "SprintStore":
        from backend.db.stores.sprint_store import SprintStore

        return SprintStore
    if name == "TeamStore":
        from backend.db.stores.team_store import TeamStore

        return TeamStore
    if name == "WorkflowStore":
        from backend.db.stores.workflow_store import WorkflowStore

        return WorkflowStore
    raise AttributeError(f"module 'backend.db.stores' has no attribute {name!r}")
