"""
Analyst tools — structured analytics artifacts.
"""

from backend.employee.tools.system_tools.base import BaseTool, ToolResult


class CreateAnalysisBriefTool(BaseTool):
    name = "create_analysis_brief"
    description = "Create a structured analytics brief with business question, data needs, and output expectations."
    category = "analytics"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "business_context": {"type": "string"},
                "metrics": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["question"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        metrics = parameters.get("metrics", [])
        metric_lines = [f"- {item}" for item in metrics] or ["- Define key metrics"]
        text = "\n".join([
            "# Analysis Brief",
            "",
            "## Business Question",
            parameters["question"],
            "",
            "## Context",
            parameters.get("business_context", "Not provided"),
            "",
            "## Key Metrics",
            *metric_lines,
            "",
            "## Required Data",
            "- Source systems",
            "- Grain",
            "- Time window",
            "- Known quality constraints",
            "",
            "## Deliverable",
            "- Summary findings",
            "- Recommendation",
            "- Caveats",
        ])
        return ToolResult(True, text, data={"analysis_brief": text})


class CreateDashboardSpecTool(BaseTool):
    name = "create_dashboard_spec"
    description = "Create a dashboard specification for analytics reporting."
    category = "analytics"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "dashboard_name": {"type": "string"},
                "audience": {"type": "string"},
                "metrics": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["dashboard_name", "audience"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        metrics = parameters.get("metrics", [])
        metric_lines = [f"- {item}" for item in metrics] or ["- Add KPI tiles"]
        text = "\n".join([
            f"# Dashboard Spec: {parameters['dashboard_name']}",
            "",
            f"Audience: {parameters['audience']}",
            "",
            "## KPI Tiles",
            *metric_lines,
            "",
            "## Visual Sections",
            "- Trends over time",
            "- Segment breakdowns",
            "- Funnel or cohort view",
            "",
            "## UX Requirements",
            "- Filters",
            "- Default date range",
            "- Drill-down behavior",
        ])
        return ToolResult(True, text, data={"dashboard_spec": text})
