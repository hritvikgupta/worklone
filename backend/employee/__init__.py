__all__ = ["EmployeeStore", "GenericEmployeeAgent"]


def __getattr__(name: str):
    if name == "EmployeeStore":
        from backend.store.employee_store import EmployeeStore

        return EmployeeStore
    if name == "GenericEmployeeAgent":
        from backend.employee.react_agent import GenericEmployeeAgent

        return GenericEmployeeAgent
    raise AttributeError(f"module 'backend.employee' has no attribute {name!r}")
