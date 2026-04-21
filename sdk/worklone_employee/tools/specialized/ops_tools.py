"""
Ops tools — structured operations artifacts.
"""

from worklone_employee.tools.base import BaseTool, ToolResult


class CreateRunbookTool(BaseTool):
    name = "create_runbook"
    description = "Create an operational runbook with steps, checks, rollback, and escalation."
    category = "operations"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "process_name": {"type": "string"},
                "objective": {"type": "string"},
                "prechecks": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["process_name", "objective"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        prechecks = parameters.get("prechecks", [])
        precheck_lines = [f"- {item}" for item in prechecks] or ["- Confirm prerequisites"]
        text = "\n".join([
            f"# Runbook: {parameters['process_name']}",
            "",
            "## Objective",
            parameters["objective"],
            "",
            "## Preconditions",
            *precheck_lines,
            "",
            "## Procedure",
            "1. Start",
            "2. Verify intermediate checks",
            "3. Complete and validate outcome",
            "",
            "## Rollback",
            "- Define reversal steps",
            "",
            "## Escalation",
            "- Define owner and escalation path",
        ])
        return ToolResult(True, text, data={"runbook": text})


class CreateIncidentReportTool(BaseTool):
    name = "create_incident_report"
    description = "Create a structured incident report with timeline, impact, root cause, and actions."
    category = "operations"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "incident_title": {"type": "string"},
                "impact_summary": {"type": "string"},
                "timeline_events": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["incident_title", "impact_summary"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        events = parameters.get("timeline_events", [])
        event_lines = [f"- {item}" for item in events] or ["- Add timeline events"]
        text = "\n".join([
            f"# Incident Report: {parameters['incident_title']}",
            "",
            "## Impact",
            parameters["impact_summary"],
            "",
            "## Timeline",
            *event_lines,
            "",
            "## Root Cause",
            "- To be completed",
            "",
            "## Corrective Actions",
            "- Immediate mitigation",
            "- Preventive follow-up",
        ])
        return ToolResult(True, text, data={"incident_report": text})
