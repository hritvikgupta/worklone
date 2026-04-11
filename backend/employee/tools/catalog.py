"""Tool catalog for DB-configured employees."""

from typing import Callable, Optional

from backend.employee.tools.integration_tools.analytics_tool import AnalyticsTool
from backend.employee.tools.data_tools.sql_tool import SQLTool
from backend.employee.tools.integration_tools.github_tool import GitHubTool
from backend.employee.tools.integration_tools.gmail_tool import GmailTool
from backend.employee.tools.integration_tools.jira_tool import JiraTool
from backend.employee.tools.integration_tools.notion_tool import NotionTool
from backend.employee.tools.integration_tools.research_tool import ResearchTool
from backend.employee.tools.integration_tools.slack_tool import SlackTool
from backend.employee.tools.run_tools.function_tool import FunctionTool
from backend.employee.tools.run_tools.llm_tool import LLMTool
from backend.employee.tools.specialized_tools.pm_tools import (
    AnalyzeCompetitorsTool,
    CreatePRDTool,
    DefineMetricsTool,
    PlanUserResearchTool,
    PrioritizeFeaturesTool,
)
from backend.employee.tools.specialized_tools.engineer_tools import (
    CreateTechnicalSpecTool,
    CreateTestPlanTool,
)
from backend.employee.tools.specialized_tools.analyst_tools import (
    CreateAnalysisBriefTool,
    CreateDashboardSpecTool,
)
from backend.employee.tools.specialized_tools.designer_tools import (
    CreateComponentSpecTool,
    CreateDesignBriefTool,
)
from backend.employee.tools.specialized_tools.recruiter_tools import (
    CreateInterviewPlanTool,
    CreateScorecardTool,
)
from backend.employee.tools.specialized_tools.sales_tools import (
    CreateAccountPlanTool,
    DraftFollowupSequenceTool,
)
from backend.employee.tools.specialized_tools.ops_tools import (
    CreateIncidentReportTool,
    CreateRunbookTool,
)
from backend.employee.tools.system_tools.base import BaseTool
from backend.employee.tools.system_tools.file_tool import FileTool
from backend.employee.tools.system_tools.http_tool import HTTPTool
from backend.employee.tools.system_tools.memory_tool import MemoryTool
from backend.employee.tools.system_tools.shell_tool import ShellTool
from backend.employee.tools.workflow_tools.coworker_tools import (
    AddBlockTool,
    ConnectBlocksTool,
    CreateWorkflowTool,
    ExecuteWorkflowTool,
    ListWorkflowsTool,
    MonitorWorkflowTool,
    SetTriggerTool,
)
from backend.employee.tools.workflow_tools.approval_tool import ApprovalTool

ToolFactory = Callable[[], BaseTool]

OPTIONAL_EMPLOYEE_TOOL_NAMES = {
    "SlackTool",
    "GmailTool",
    "JiraTool",
    "NotionTool",
    "AnalyticsTool",
    "ResearchTool",
    "GitHubTool",
}


def _build_catalog() -> dict[str, ToolFactory]:
    catalog: dict[str, ToolFactory] = {}

    def add(factory: ToolFactory, *aliases: str) -> None:
        for alias in aliases:
            catalog[alias.lower()] = factory

    add(SlackTool, "SlackTool", "slack_send")
    add(GmailTool, "GmailTool", "gmail")
    add(HTTPTool, "HTTPTool", "http_request")
    add(FileTool, "FileTool", "file_operations")
    add(ShellTool, "ShellTool", "run_shell")
    add(MemoryTool, "MemoryTool", "memory_store")
    add(FunctionTool, "FunctionTool", "run_function")
    add(LLMTool, "LLMTool", "call_llm")
    add(SQLTool, "SQLTool", "run_sql")
    add(JiraTool, "JiraTool", "jira")
    add(NotionTool, "NotionTool", "notion")
    add(AnalyticsTool, "AnalyticsTool", "analytics")
    add(ResearchTool, "ResearchTool", "research")
    add(GitHubTool, "GitHubTool", "github")
    add(PrioritizeFeaturesTool, "PrioritizeFeaturesTool", "prioritize_features")
    add(CreatePRDTool, "CreatePRDTool", "create_prd")
    add(AnalyzeCompetitorsTool, "AnalyzeCompetitorsTool", "analyze_competitors")
    add(DefineMetricsTool, "DefineMetricsTool", "define_metrics")
    add(PlanUserResearchTool, "PlanUserResearchTool", "plan_user_research")
    add(CreateTechnicalSpecTool, "CreateTechnicalSpecTool", "create_technical_spec")
    add(CreateTestPlanTool, "CreateTestPlanTool", "create_test_plan")
    add(CreateAnalysisBriefTool, "CreateAnalysisBriefTool", "create_analysis_brief")
    add(CreateDashboardSpecTool, "CreateDashboardSpecTool", "create_dashboard_spec")
    add(CreateDesignBriefTool, "CreateDesignBriefTool", "create_design_brief")
    add(CreateComponentSpecTool, "CreateComponentSpecTool", "create_component_spec")
    add(CreateInterviewPlanTool, "CreateInterviewPlanTool", "create_interview_plan")
    add(CreateScorecardTool, "CreateScorecardTool", "create_candidate_scorecard")
    add(CreateAccountPlanTool, "CreateAccountPlanTool", "create_account_plan")
    add(DraftFollowupSequenceTool, "DraftFollowupSequenceTool", "draft_followup_sequence")
    add(CreateRunbookTool, "CreateRunbookTool", "create_runbook")
    add(CreateIncidentReportTool, "CreateIncidentReportTool", "create_incident_report")
    add(CreateWorkflowTool, "CreateWorkflowTool", "create_workflow")
    add(AddBlockTool, "AddBlockTool", "add_block")
    add(ConnectBlocksTool, "ConnectBlocksTool", "connect_blocks")
    add(SetTriggerTool, "SetTriggerTool", "set_trigger")
    add(ExecuteWorkflowTool, "ExecuteWorkflowTool", "execute_workflow")
    add(ListWorkflowsTool, "ListWorkflowsTool", "list_workflows")
    add(MonitorWorkflowTool, "MonitorWorkflowTool", "monitor_workflow")
    add(ApprovalTool, "ApprovalTool", "manage_approval")

    return catalog


TOOL_CATALOG = _build_catalog()


def list_catalog_tools() -> list[dict]:
    """Return canonical tool metadata for UI and runtime use."""
    tools = []
    seen: set[str] = set()

    for factory in TOOL_CATALOG.values():
        tool = factory()
        class_name = tool.__class__.__name__
        if class_name in seen:
            continue
        seen.add(class_name)
        tools.append({
            "name": class_name,
            "runtime_name": tool.name,
            "description": tool.description,
            "category": tool.category,
            "is_optional": class_name in OPTIONAL_EMPLOYEE_TOOL_NAMES,
            "is_default": class_name not in OPTIONAL_EMPLOYEE_TOOL_NAMES,
        })

    tools.sort(key=lambda item: (item["category"], item["name"]))
    return tools


DEFAULT_EMPLOYEE_TOOL_NAMES = {
    tool["name"]
    for tool in list_catalog_tools()
    if tool["is_default"]
}


def create_tool(tool_name: str) -> Optional[BaseTool]:
    """Instantiate a tool from either its UI label or runtime name."""
    if not tool_name:
        return None
    factory = TOOL_CATALOG.get(tool_name.strip().lower())
    if not factory:
        return None
    return factory()
