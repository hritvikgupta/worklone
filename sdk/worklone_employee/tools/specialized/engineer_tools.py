"""
Engineer tools — structured engineering artifacts.
"""

from datetime import datetime

from worklone_employee.tools.base import BaseTool, ToolResult


class CreateTechnicalSpecTool(BaseTool):
    name = "create_technical_spec"
    description = "Create a structured technical specification for an engineering task."
    category = "engineering"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "feature_name": {"type": "string"},
                "objective": {"type": "string"},
                "constraints": {"type": "array", "items": {"type": "string"}},
                "acceptance_criteria": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["feature_name", "objective"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        constraints = parameters.get("constraints", [])
        acceptance = parameters.get("acceptance_criteria", [])
        constraint_lines = [f"- {item}" for item in constraints] or ["- None provided"]
        acceptance_lines = [f"- {item}" for item in acceptance] or ["- Define success conditions"]
        spec = [
            f"# Technical Spec: {parameters['feature_name']}",
            "",
            "## Objective",
            parameters["objective"],
            "",
            "## Constraints",
            *constraint_lines,
            "",
            "## Proposed Approach",
            "- Architecture changes",
            "- Data model changes",
            "- API and integration impacts",
            "- Observability and rollback plan",
            "",
            "## Acceptance Criteria",
            *acceptance_lines,
            "",
            f"Created: {datetime.utcnow().strftime('%Y-%m-%d')}",
        ]
        text = "\n".join(spec)
        return ToolResult(True, text, data={"technical_spec": text})


class CreateTestPlanTool(BaseTool):
    name = "create_test_plan"
    description = "Create a structured test plan for an engineering change."
    category = "engineering"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "system_under_test": {"type": "string"},
                "change_summary": {"type": "string"},
                "test_scenarios": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["system_under_test", "change_summary"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        scenarios = parameters.get("test_scenarios", [])
        scenario_lines = [f"- {item}" for item in scenarios] or ["- Add target scenarios"]
        text = "\n".join([
            f"# Test Plan: {parameters['system_under_test']}",
            "",
            "## Change Summary",
            parameters["change_summary"],
            "",
            "## Test Coverage",
            "- Unit tests",
            "- Integration tests",
            "- Regression checks",
            "- Failure and rollback cases",
            "",
            "## Scenarios",
            *scenario_lines,
        ])
        return ToolResult(True, text, data={"test_plan": text})
