"""
Sales tools — structured sales artifacts.
"""

from backend.core.tools.system_tools.base import BaseTool, ToolResult


class CreateAccountPlanTool(BaseTool):
    name = "create_account_plan"
    description = "Create an account plan covering objectives, stakeholders, risks, and next steps."
    category = "sales"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "account_name": {"type": "string"},
                "objective": {"type": "string"},
                "stakeholders": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["account_name", "objective"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        stakeholders = parameters.get("stakeholders", [])
        stakeholder_lines = [f"- {item}" for item in stakeholders] or ["- Add buyer map"]
        text = "\n".join([
            f"# Account Plan: {parameters['account_name']}",
            "",
            "## Objective",
            parameters["objective"],
            "",
            "## Stakeholders",
            *stakeholder_lines,
            "",
            "## Risks",
            "- Budget",
            "- Timing",
            "- Competitive pressure",
            "",
            "## Next Steps",
            "- Discovery",
            "- Mutual action plan",
            "- Decision process clarification",
        ])
        return ToolResult(True, text, data={"account_plan": text})


class DraftFollowupSequenceTool(BaseTool):
    name = "draft_followup_sequence"
    description = "Create a concise multi-step sales follow-up sequence."
    category = "sales"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "prospect_name": {"type": "string"},
                "company": {"type": "string"},
                "goal": {"type": "string"},
            },
            "required": ["goal"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        text = "\n".join([
            "# Follow-up Sequence",
            "",
            f"Prospect: {parameters.get('prospect_name', 'Unknown')} at {parameters.get('company', 'Unknown company')}",
            f"Goal: {parameters['goal']}",
            "",
            "Day 1: Short recap and clear CTA",
            "Day 3: Send relevant proof point or case study",
            "Day 7: Reframe around business impact",
            "Day 12: Close-the-loop note",
        ])
        return ToolResult(True, text, data={"followup_sequence": text})
