"""
Approval Tool — request and track human approvals.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from backend.employee.tools.system_tools.base import BaseTool, ToolResult


class ApprovalTool(BaseTool):
    """Persist lightweight approval requests and decisions."""

    name = "manage_approval"
    description = "Request approval, list approvals, and record approval decisions."
    category = "workflow"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["request_approval", "list_approvals", "respond_approval"],
                },
                "approval_id": {"type": "string"},
                "title": {"type": "string"},
                "details": {"type": "string"},
                "decision": {"type": "string", "enum": ["approved", "rejected"]},
                "resolver": {"type": "string"},
                "status": {"type": "string", "enum": ["pending", "approved", "rejected"]},
            },
            "required": ["action"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        action = parameters.get("action")
        approvals = self._load_approvals()

        if action == "request_approval":
            employee_id = (context or {}).get("employee_id") or "employee"
            item = {
                "id": parameters.get("approval_id") or f"appr_{uuid4().hex[:12]}",
                "title": parameters.get("title", "").strip() or "Approval request",
                "details": parameters.get("details", ""),
                "status": "pending",
                "requested_by": employee_id,
                "requested_at": datetime.utcnow().isoformat(),
                "resolver": None,
                "resolved_at": None,
                "decision": None,
            }
            approvals.append(item)
            self._save_approvals(approvals)
            return ToolResult(True, f"Requested approval {item['id']}", data=item)

        if action == "list_approvals":
            status = parameters.get("status")
            items = [item for item in approvals if not status or item.get("status") == status]
            return ToolResult(True, json.dumps(items[:100], indent=2), data={"approvals": items[:100]})

        if action == "respond_approval":
            approval_id = parameters.get("approval_id", "")
            decision = parameters.get("decision")
            if decision not in {"approved", "rejected"}:
                return ToolResult(False, "", error="decision must be approved or rejected")
            for item in approvals:
                if item["id"] == approval_id:
                    item["status"] = decision
                    item["decision"] = decision
                    item["resolver"] = parameters.get("resolver") or (context or {}).get("user_id") or "human"
                    item["resolved_at"] = datetime.utcnow().isoformat()
                    self._save_approvals(approvals)
                    return ToolResult(True, f"{decision.title()} approval {approval_id}", data=item)
            return ToolResult(False, "", error=f"Approval not found: {approval_id}")

        return ToolResult(False, "", error=f"Unknown action: {action}")

    def _approval_file(self) -> Path:
        data_dir = Path(__file__).resolve().parents[2] / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir / "approvals.json"

    def _load_approvals(self) -> list[dict]:
        path = self._approval_file()
        if not path.exists():
            return []
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _save_approvals(self, approvals: list[dict]) -> None:
        self._approval_file().write_text(json.dumps(approvals, indent=2), encoding="utf-8")
