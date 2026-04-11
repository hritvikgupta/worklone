"""
Designer tools — structured design artifacts.
"""

from backend.employee.tools.system_tools.base import BaseTool, ToolResult


class CreateDesignBriefTool(BaseTool):
    name = "create_design_brief"
    description = "Create a design brief covering goals, constraints, and user experience needs."
    category = "design"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "project_name": {"type": "string"},
                "goal": {"type": "string"},
                "target_users": {"type": "string"},
                "constraints": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["project_name", "goal"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        constraints = parameters.get("constraints", [])
        constraint_lines = [f"- {item}" for item in constraints] or ["- None provided"]
        text = "\n".join([
            f"# Design Brief: {parameters['project_name']}",
            "",
            "## Goal",
            parameters["goal"],
            "",
            "## Target Users",
            parameters.get("target_users", "Not provided"),
            "",
            "## Constraints",
            *constraint_lines,
            "",
            "## Deliverables",
            "- Flows",
            "- Key screens",
            "- States and edge cases",
            "- Accessibility notes",
        ])
        return ToolResult(True, text, data={"design_brief": text})


class CreateComponentSpecTool(BaseTool):
    name = "create_component_spec"
    description = "Create a UI component specification with states, props, and accessibility notes."
    category = "design"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "component_name": {"type": "string"},
                "purpose": {"type": "string"},
                "states": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["component_name", "purpose"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        states = parameters.get("states", [])
        state_lines = [f"- {item}" for item in states] or ["- Default", "- Hover", "- Disabled", "- Error"]
        text = "\n".join([
            f"# Component Spec: {parameters['component_name']}",
            "",
            "## Purpose",
            parameters["purpose"],
            "",
            "## States",
            *state_lines,
            "",
            "## Notes",
            "- Accessibility behavior",
            "- Content rules",
            "- Responsive behavior",
            "- Empty/loading/error states",
        ])
        return ToolResult(True, text, data={"component_spec": text})
