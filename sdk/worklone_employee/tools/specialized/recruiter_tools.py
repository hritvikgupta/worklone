"""
Recruiter tools — structured hiring artifacts.
"""

from worklone_employee.tools.base import BaseTool, ToolResult


class CreateInterviewPlanTool(BaseTool):
    name = "create_interview_plan"
    description = "Create an interview plan with stages, focus areas, and evaluation criteria."
    category = "recruiting"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "role_title": {"type": "string"},
                "level": {"type": "string"},
                "focus_areas": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["role_title"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        focus = parameters.get("focus_areas", [])
        focus_lines = [f"- {item}" for item in focus] or ["- Technical depth", "- Communication", "- Role fit"]
        text = "\n".join([
            f"# Interview Plan: {parameters['role_title']}",
            f"Level: {parameters.get('level', 'Not provided')}",
            "",
            "## Focus Areas",
            *focus_lines,
            "",
            "## Suggested Stages",
            "- Recruiter screen",
            "- Hiring manager interview",
            "- Functional assessment",
            "- Final panel",
        ])
        return ToolResult(True, text, data={"interview_plan": text})


class CreateScorecardTool(BaseTool):
    name = "create_candidate_scorecard"
    description = "Create a candidate scorecard with clear evaluation dimensions."
    category = "recruiting"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "role_title": {"type": "string"},
                "competencies": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["role_title"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        competencies = parameters.get("competencies", [])
        competency_lines = [f"- {item}: 1-5 with evidence" for item in competencies] or ["- Problem solving: 1-5 with evidence"]
        text = "\n".join([
            f"# Candidate Scorecard: {parameters['role_title']}",
            "",
            "## Competencies",
            *competency_lines,
            "",
            "## Overall Recommendation",
            "- Strong hire",
            "- Hire",
            "- Lean no",
            "- No hire",
        ])
        return ToolResult(True, text, data={"scorecard": text})
