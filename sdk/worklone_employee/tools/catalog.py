"""Tool catalog — SDK edition. Only standalone system tools, no OAuth integrations."""

from typing import Callable, Optional

from worklone_employee.tools.base import BaseTool
from worklone_employee.tools.data.sql_tool import SQLTool
from worklone_employee.tools.run.function_tool import FunctionTool
from worklone_employee.tools.run.llm_tool import LLMTool
from worklone_employee.tools.system.file_tool import FileTool
from worklone_employee.tools.system.http_tool import HTTPTool
from worklone_employee.tools.system.memory_tool import MemoryTool
from worklone_employee.tools.system.shell_tool import ShellTool
from worklone_employee.tools.system.session_search_tool import SessionSearchTool
from worklone_employee.tools.system.web_search_tool import WebSearchTool
from worklone_employee.tools.system.web_extract_tool import WebExtractTool
from worklone_employee.tools.employee.task_tool import TaskTool
from worklone_employee.tools.employee.ask_user_tool import AskUserTool
from worklone_employee.tools.employee.run_task_tool import RunTaskTool
from worklone_employee.tools.workflow.approval_tool import ApprovalTool
from worklone_employee.tools.specialized.pm_tools import (
    AnalyzeCompetitorsTool, CreatePRDTool, DefineMetricsTool,
    PlanUserResearchTool, PrioritizeFeaturesTool,
)
from worklone_employee.tools.specialized.engineer_tools import (
    CreateTechnicalSpecTool, CreateTestPlanTool,
)
from worklone_employee.tools.specialized.analyst_tools import (
    CreateAnalysisBriefTool, CreateDashboardSpecTool,
)
from worklone_employee.tools.specialized.designer_tools import (
    CreateComponentSpecTool, CreateDesignBriefTool,
)
from worklone_employee.tools.specialized.recruiter_tools import (
    CreateInterviewPlanTool, CreateScorecardTool,
)
from worklone_employee.tools.specialized.sales_tools import (
    CreateAccountPlanTool, DraftFollowupSequenceTool,
)
from worklone_employee.tools.specialized.ops_tools import (
    CreateIncidentReportTool, CreateRunbookTool,
)

ToolFactory = Callable[[], BaseTool]

# runtime_name -> factory
TOOL_CATALOG: dict[str, ToolFactory] = {
    # System
    "http_request":     HTTPTool,
    "file_operations":  FileTool,
    "run_shell":        ShellTool,
    "memory_store":     MemoryTool,
    "run_function":     FunctionTool,
    "call_llm":         LLMTool,
    "run_sql":          SQLTool,
    "session_search":   SessionSearchTool,
    "web_search":       WebSearchTool,
    "web_extract":      WebExtractTool,
    # Employee core
    "manage_tasks":     TaskTool,
    "ask_user":         AskUserTool,
    "run_task_async":   RunTaskTool,
    "manage_approval":  ApprovalTool,
    # Specialized
    "prioritize_features":      PrioritizeFeaturesTool,
    "create_prd":               CreatePRDTool,
    "analyze_competitors":      AnalyzeCompetitorsTool,
    "define_metrics":           DefineMetricsTool,
    "plan_user_research":       PlanUserResearchTool,
    "create_technical_spec":    CreateTechnicalSpecTool,
    "create_test_plan":         CreateTestPlanTool,
    "create_analysis_brief":    CreateAnalysisBriefTool,
    "create_dashboard_spec":    CreateDashboardSpecTool,
    "create_design_brief":      CreateDesignBriefTool,
    "create_component_spec":    CreateComponentSpecTool,
    "create_interview_plan":    CreateInterviewPlanTool,
    "create_candidate_scorecard": CreateScorecardTool,
    "create_account_plan":      CreateAccountPlanTool,
    "draft_followup_sequence":  DraftFollowupSequenceTool,
    "create_runbook":           CreateRunbookTool,
    "create_incident_report":   CreateIncidentReportTool,
}

# Tools always loaded for every employee
DEFAULT_EMPLOYEE_TOOL_NAMES = {
    "http_request", "file_operations", "run_shell", "memory_store",
    "run_function", "call_llm", "run_sql", "session_search",
    "web_search", "web_extract",
    "manage_tasks", "ask_user", "run_task_async",
    "prioritize_features", "create_prd", "analyze_competitors",
    "define_metrics", "plan_user_research", "create_technical_spec",
    "create_test_plan", "create_analysis_brief", "create_dashboard_spec",
    "create_design_brief", "create_component_spec", "create_interview_plan",
    "create_candidate_scorecard", "create_account_plan",
    "draft_followup_sequence", "create_runbook", "create_incident_report",
}


def create_tool(tool_name: str) -> Optional[BaseTool]:
    factory = TOOL_CATALOG.get((tool_name or "").strip().lower())
    return factory() if factory else None


def expand_tool_selection(tool_names: list[str]) -> list[str]:
    """Pass-through — no bundles in the SDK, names are already runtime names."""
    seen: set[str] = set()
    result = []
    for name in tool_names:
        n = (name or "").strip().lower()
        if n and n not in seen:
            result.append(n)
            seen.add(n)
    return result
