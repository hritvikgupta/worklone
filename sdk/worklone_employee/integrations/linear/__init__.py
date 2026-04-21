"""
Linear integration for worklone-employee SDK.
"""
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode
import httpx
from worklone_employee.integrations.base import OAuthIntegration, OAuthIntegration
from worklone_employee.tools.base import BaseTool

from worklone_employee.integrations.linear.add_label_to_issue import LinearAddLabelToIssueTool
from worklone_employee.integrations.linear.add_label_to_project import LinearAddLabelToProjectTool
from worklone_employee.integrations.linear.archive_issue import LinearArchiveIssueTool
from worklone_employee.integrations.linear.archive_label import LinearArchiveLabelTool
from worklone_employee.integrations.linear.archive_project import LinearArchiveProjectTool
from worklone_employee.integrations.linear.create_attachment import LinearCreateAttachmentTool
from worklone_employee.integrations.linear.create_comment import LinearCreateCommentTool
from worklone_employee.integrations.linear.create_customer import LinearCreateCustomerTool
from worklone_employee.integrations.linear.create_customer_request import LinearCreateCustomerRequestTool
from worklone_employee.integrations.linear.create_customer_status import LinearCreateCustomerStatusTool
from worklone_employee.integrations.linear.create_customer_tier import LinearCreateCustomerTierTool
from worklone_employee.integrations.linear.create_cycle import LinearCreateCycleTool
from worklone_employee.integrations.linear.create_favorite import LinearCreateFavoriteTool
from worklone_employee.integrations.linear.create_issue import LinearCreateIssueTool
from worklone_employee.integrations.linear.create_issue_relation import LinearCreateIssueRelationTool
from worklone_employee.integrations.linear.create_label import LinearCreateLabelTool
from worklone_employee.integrations.linear.create_project import LinearCreateProjectTool
from worklone_employee.integrations.linear.create_project_label import LinearCreateProjectLabelTool
from worklone_employee.integrations.linear.create_project_milestone import LinearCreateProjectMilestoneTool
from worklone_employee.integrations.linear.create_project_status import LinearCreateProjectStatusTool
from worklone_employee.integrations.linear.create_project_update import LinearCreateProjectUpdateTool
from worklone_employee.integrations.linear.create_workflow_state import LinearCreateWorkflowStateTool
from worklone_employee.integrations.linear.delete_attachment import LinearDeleteAttachmentTool
from worklone_employee.integrations.linear.delete_comment import LinearDeleteCommentTool
from worklone_employee.integrations.linear.delete_customer import LinearDeleteCustomerTool
from worklone_employee.integrations.linear.delete_customer_status import LinearDeleteCustomerStatusTool
from worklone_employee.integrations.linear.delete_customer_tier import LinearDeleteCustomerTierTool
from worklone_employee.integrations.linear.delete_issue import LinearDeleteIssueTool
from worklone_employee.integrations.linear.delete_issue_relation import LinearDeleteIssueRelationTool
from worklone_employee.integrations.linear.delete_project import LinearDeleteProjectTool
from worklone_employee.integrations.linear.delete_project_label import LinearDeleteProjectLabelTool
from worklone_employee.integrations.linear.delete_project_milestone import LinearDeleteProjectMilestoneTool
from worklone_employee.integrations.linear.delete_project_status import LinearDeleteProjectStatusTool
from worklone_employee.integrations.linear.get_active_cycle import LinearGetActiveCycleTool
from worklone_employee.integrations.linear.get_customer import LinearGetCustomerTool
from worklone_employee.integrations.linear.get_cycle import LinearGetCycleTool
from worklone_employee.integrations.linear.get_issue import LinearGetIssueTool
from worklone_employee.integrations.linear.get_project import LinearGetProjectTool
from worklone_employee.integrations.linear.get_viewer import LinearGetViewerTool
from worklone_employee.integrations.linear.list_attachments import LinearListAttachmentsTool
from worklone_employee.integrations.linear.list_comments import LinearListCommentsTool
from worklone_employee.integrations.linear.list_customer_requests import LinearListCustomerRequestsTool
from worklone_employee.integrations.linear.list_customer_statuses import LinearListCustomerStatusesTool
from worklone_employee.integrations.linear.list_customer_tiers import LinearListCustomerTiersTool
from worklone_employee.integrations.linear.list_customers import LinearListCustomersTool
from worklone_employee.integrations.linear.list_cycles import LinearListCyclesTool
from worklone_employee.integrations.linear.list_favorites import LinearListFavoritesTool
from worklone_employee.integrations.linear.list_issue_relations import LinearListIssueRelationsTool
from worklone_employee.integrations.linear.list_labels import LinearListLabelsTool
from worklone_employee.integrations.linear.list_notifications import LinearListNotificationsTool
from worklone_employee.integrations.linear.list_project_labels import LinearListProjectLabelsTool
from worklone_employee.integrations.linear.list_project_milestones import LinearListProjectMilestonesTool
from worklone_employee.integrations.linear.list_project_statuses import LinearListProjectStatusesTool
from worklone_employee.integrations.linear.list_project_updates import LinearListProjectUpdatesTool
from worklone_employee.integrations.linear.list_projects import LinearListProjectsTool
from worklone_employee.integrations.linear.list_teams import LinearListTeamsTool
from worklone_employee.integrations.linear.list_users import LinearListUsersTool
from worklone_employee.integrations.linear.list_workflow_states import LinearListWorkflowStatesTool
from worklone_employee.integrations.linear.merge_customers import LinearMergeCustomersTool
from worklone_employee.integrations.linear.read_issues import LinearReadIssuesTool
from worklone_employee.integrations.linear.remove_label_from_issue import LinearRemoveLabelFromIssueTool
from worklone_employee.integrations.linear.remove_label_from_project import LinearRemoveLabelFromProjectTool
from worklone_employee.integrations.linear.search_issues import LinearSearchIssuesTool
from worklone_employee.integrations.linear.unarchive_issue import LinearUnarchiveIssueTool
from worklone_employee.integrations.linear.update_attachment import LinearUpdateAttachmentTool
from worklone_employee.integrations.linear.update_comment import LinearUpdateCommentTool
from worklone_employee.integrations.linear.update_customer import LinearUpdateCustomerTool
from worklone_employee.integrations.linear.update_customer_request import LinearUpdateCustomerRequestTool
from worklone_employee.integrations.linear.update_customer_status import LinearUpdateCustomerStatusTool
from worklone_employee.integrations.linear.update_customer_tier import LinearUpdateCustomerTierTool
from worklone_employee.integrations.linear.update_issue import LinearUpdateIssueTool
from worklone_employee.integrations.linear.update_label import LinearUpdateLabelTool
from worklone_employee.integrations.linear.update_notification import LinearUpdateNotificationTool
from worklone_employee.integrations.linear.update_project import LinearUpdateProjectTool
from worklone_employee.integrations.linear.update_project_label import LinearUpdateProjectLabelTool
from worklone_employee.integrations.linear.update_project_milestone import LinearUpdateProjectMilestoneTool
from worklone_employee.integrations.linear.update_project_status import LinearUpdateProjectStatusTool
from worklone_employee.integrations.linear.update_workflow_state import LinearUpdateWorkflowStateTool

_TOOL_CLASSES = [
    LinearAddLabelToIssueTool, LinearAddLabelToProjectTool, LinearArchiveIssueTool, LinearArchiveLabelTool, LinearArchiveProjectTool, LinearCreateAttachmentTool, LinearCreateCommentTool, LinearCreateCustomerTool, LinearCreateCustomerRequestTool, LinearCreateCustomerStatusTool, LinearCreateCustomerTierTool, LinearCreateCycleTool, LinearCreateFavoriteTool, LinearCreateIssueTool, LinearCreateIssueRelationTool, LinearCreateLabelTool, LinearCreateProjectTool, LinearCreateProjectLabelTool, LinearCreateProjectMilestoneTool, LinearCreateProjectStatusTool, LinearCreateProjectUpdateTool, LinearCreateWorkflowStateTool, LinearDeleteAttachmentTool, LinearDeleteCommentTool, LinearDeleteCustomerTool, LinearDeleteCustomerStatusTool, LinearDeleteCustomerTierTool, LinearDeleteIssueTool, LinearDeleteIssueRelationTool, LinearDeleteProjectTool, LinearDeleteProjectLabelTool, LinearDeleteProjectMilestoneTool, LinearDeleteProjectStatusTool, LinearGetActiveCycleTool, LinearGetCustomerTool, LinearGetCycleTool, LinearGetIssueTool, LinearGetProjectTool, LinearGetViewerTool, LinearListAttachmentsTool, LinearListCommentsTool, LinearListCustomerRequestsTool, LinearListCustomerStatusesTool, LinearListCustomerTiersTool, LinearListCustomersTool, LinearListCyclesTool, LinearListFavoritesTool, LinearListIssueRelationsTool, LinearListLabelsTool, LinearListNotificationsTool, LinearListProjectLabelsTool, LinearListProjectMilestonesTool, LinearListProjectStatusesTool, LinearListProjectUpdatesTool, LinearListProjectsTool, LinearListTeamsTool, LinearListUsersTool, LinearListWorkflowStatesTool, LinearMergeCustomersTool, LinearReadIssuesTool, LinearRemoveLabelFromIssueTool, LinearRemoveLabelFromProjectTool, LinearSearchIssuesTool, LinearUnarchiveIssueTool, LinearUpdateAttachmentTool, LinearUpdateCommentTool, LinearUpdateCustomerTool, LinearUpdateCustomerRequestTool, LinearUpdateCustomerStatusTool, LinearUpdateCustomerTierTool, LinearUpdateIssueTool, LinearUpdateLabelTool, LinearUpdateNotificationTool, LinearUpdateProjectTool, LinearUpdateProjectLabelTool, LinearUpdateProjectMilestoneTool, LinearUpdateProjectStatusTool, LinearUpdateWorkflowStateTool,
]

def _wire(tool: BaseTool, integration) -> BaseTool:
    async def _resolve_access_token(context=None):
        user_id = (context or {}).get("user_id") or (context or {}).get("owner_id")
        if not user_id:
            raise ValueError("user_id missing from context — pass user_id when calling emp.run()")
        return await integration._get_token(user_id)
    tool._resolve_access_token = _resolve_access_token
    return tool


class Linear(OAuthIntegration):
    PROVIDER = "linear"
    """Linear OAuth. Also accepts a personal API key as access_token."""

    _AUTH_BASE = "https://linear.app/oauth/authorize"
    _TOKEN_URL = "https://api.linear.app/oauth/token"
    SCOPES = ['read', 'write']

    @classmethod
    def get_auth_url(cls, client_id: str, redirect_uri: str, scopes: Optional[List[str]] = None) -> str:
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes or cls.SCOPES),
        }
        return f"{cls._AUTH_BASE}?{urlencode(params)}"

    @classmethod
    async def exchange_code(cls, code: str, client_id: str, client_secret: str, redirect_uri: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(cls._TOKEN_URL, data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
            })
            resp.raise_for_status()
            return resp.json()

    async def _do_refresh(self) -> None:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(self._TOKEN_URL, data={
                "grant_type": "refresh_token",
                "refresh_token": self._refresh_token,
                "client_id": self._client_id,
                "client_secret": self._client_secret,
            })
            resp.raise_for_status()
            data = resp.json()
            self._access_token = data["access_token"]
            if "refresh_token" in data:
                self._refresh_token = data["refresh_token"]
            await self._notify_refresh()

    def __init__(self, client_id: str, client_secret: str, token_store: "TokenStore"):
        super().__init__(client_id, client_secret, token_store)


    def all(self) -> List[BaseTool]:
        return [_wire(cls(), self) for cls in _TOOL_CLASSES]

    @property
    def add_label_to_issue(self): return _wire(LinearAddLabelToIssueTool(), self)
    @property
    def add_label_to_project(self): return _wire(LinearAddLabelToProjectTool(), self)
    @property
    def archive_issue(self): return _wire(LinearArchiveIssueTool(), self)
    @property
    def archive_label(self): return _wire(LinearArchiveLabelTool(), self)
    @property
    def archive_project(self): return _wire(LinearArchiveProjectTool(), self)
    @property
    def create_attachment(self): return _wire(LinearCreateAttachmentTool(), self)
    @property
    def create_comment(self): return _wire(LinearCreateCommentTool(), self)
    @property
    def create_customer(self): return _wire(LinearCreateCustomerTool(), self)
    @property
    def create_customer_request(self): return _wire(LinearCreateCustomerRequestTool(), self)
    @property
    def create_customer_status(self): return _wire(LinearCreateCustomerStatusTool(), self)
    @property
    def create_customer_tier(self): return _wire(LinearCreateCustomerTierTool(), self)
    @property
    def create_cycle(self): return _wire(LinearCreateCycleTool(), self)
    @property
    def create_favorite(self): return _wire(LinearCreateFavoriteTool(), self)
    @property
    def create_issue(self): return _wire(LinearCreateIssueTool(), self)
    @property
    def create_issue_relation(self): return _wire(LinearCreateIssueRelationTool(), self)
    @property
    def create_label(self): return _wire(LinearCreateLabelTool(), self)
    @property
    def create_project(self): return _wire(LinearCreateProjectTool(), self)
    @property
    def create_project_label(self): return _wire(LinearCreateProjectLabelTool(), self)
    @property
    def create_project_milestone(self): return _wire(LinearCreateProjectMilestoneTool(), self)
    @property
    def create_project_status(self): return _wire(LinearCreateProjectStatusTool(), self)
    @property
    def create_project_update(self): return _wire(LinearCreateProjectUpdateTool(), self)
    @property
    def create_workflow_state(self): return _wire(LinearCreateWorkflowStateTool(), self)
    @property
    def delete_attachment(self): return _wire(LinearDeleteAttachmentTool(), self)
    @property
    def delete_comment(self): return _wire(LinearDeleteCommentTool(), self)
    @property
    def delete_customer(self): return _wire(LinearDeleteCustomerTool(), self)
    @property
    def delete_customer_status(self): return _wire(LinearDeleteCustomerStatusTool(), self)
    @property
    def delete_customer_tier(self): return _wire(LinearDeleteCustomerTierTool(), self)
    @property
    def delete_issue(self): return _wire(LinearDeleteIssueTool(), self)
    @property
    def delete_issue_relation(self): return _wire(LinearDeleteIssueRelationTool(), self)
    @property
    def delete_project(self): return _wire(LinearDeleteProjectTool(), self)
    @property
    def delete_project_label(self): return _wire(LinearDeleteProjectLabelTool(), self)
    @property
    def delete_project_milestone(self): return _wire(LinearDeleteProjectMilestoneTool(), self)
    @property
    def delete_project_status(self): return _wire(LinearDeleteProjectStatusTool(), self)
    @property
    def get_active_cycle(self): return _wire(LinearGetActiveCycleTool(), self)
    @property
    def get_customer(self): return _wire(LinearGetCustomerTool(), self)
    @property
    def get_cycle(self): return _wire(LinearGetCycleTool(), self)
    @property
    def get_issue(self): return _wire(LinearGetIssueTool(), self)
    @property
    def get_project(self): return _wire(LinearGetProjectTool(), self)
    @property
    def get_viewer(self): return _wire(LinearGetViewerTool(), self)
    @property
    def list_attachments(self): return _wire(LinearListAttachmentsTool(), self)
    @property
    def list_comments(self): return _wire(LinearListCommentsTool(), self)
    @property
    def list_customer_requests(self): return _wire(LinearListCustomerRequestsTool(), self)
    @property
    def list_customer_statuses(self): return _wire(LinearListCustomerStatusesTool(), self)
    @property
    def list_customer_tiers(self): return _wire(LinearListCustomerTiersTool(), self)
    @property
    def list_customers(self): return _wire(LinearListCustomersTool(), self)
    @property
    def list_cycles(self): return _wire(LinearListCyclesTool(), self)
    @property
    def list_favorites(self): return _wire(LinearListFavoritesTool(), self)
    @property
    def list_issue_relations(self): return _wire(LinearListIssueRelationsTool(), self)
    @property
    def list_labels(self): return _wire(LinearListLabelsTool(), self)
    @property
    def list_notifications(self): return _wire(LinearListNotificationsTool(), self)
    @property
    def list_project_labels(self): return _wire(LinearListProjectLabelsTool(), self)
    @property
    def list_project_milestones(self): return _wire(LinearListProjectMilestonesTool(), self)
    @property
    def list_project_statuses(self): return _wire(LinearListProjectStatusesTool(), self)
    @property
    def list_project_updates(self): return _wire(LinearListProjectUpdatesTool(), self)
    @property
    def list_projects(self): return _wire(LinearListProjectsTool(), self)
    @property
    def list_teams(self): return _wire(LinearListTeamsTool(), self)
    @property
    def list_users(self): return _wire(LinearListUsersTool(), self)
    @property
    def list_workflow_states(self): return _wire(LinearListWorkflowStatesTool(), self)
    @property
    def merge_customers(self): return _wire(LinearMergeCustomersTool(), self)
    @property
    def read_issues(self): return _wire(LinearReadIssuesTool(), self)
    @property
    def remove_label_from_issue(self): return _wire(LinearRemoveLabelFromIssueTool(), self)
    @property
    def remove_label_from_project(self): return _wire(LinearRemoveLabelFromProjectTool(), self)
    @property
    def search_issues(self): return _wire(LinearSearchIssuesTool(), self)
    @property
    def unarchive_issue(self): return _wire(LinearUnarchiveIssueTool(), self)
    @property
    def update_attachment(self): return _wire(LinearUpdateAttachmentTool(), self)
    @property
    def update_comment(self): return _wire(LinearUpdateCommentTool(), self)
    @property
    def update_customer(self): return _wire(LinearUpdateCustomerTool(), self)
    @property
    def update_customer_request(self): return _wire(LinearUpdateCustomerRequestTool(), self)
    @property
    def update_customer_status(self): return _wire(LinearUpdateCustomerStatusTool(), self)
    @property
    def update_customer_tier(self): return _wire(LinearUpdateCustomerTierTool(), self)
    @property
    def update_issue(self): return _wire(LinearUpdateIssueTool(), self)
    @property
    def update_label(self): return _wire(LinearUpdateLabelTool(), self)
    @property
    def update_notification(self): return _wire(LinearUpdateNotificationTool(), self)
    @property
    def update_project(self): return _wire(LinearUpdateProjectTool(), self)
    @property
    def update_project_label(self): return _wire(LinearUpdateProjectLabelTool(), self)
    @property
    def update_project_milestone(self): return _wire(LinearUpdateProjectMilestoneTool(), self)
    @property
    def update_project_status(self): return _wire(LinearUpdateProjectStatusTool(), self)
    @property
    def update_workflow_state(self): return _wire(LinearUpdateWorkflowStateTool(), self)
