"""
Jira integration for worklone-employee SDK.
"""
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode
import httpx
from worklone_employee.integrations.base import OAuthIntegration, OAuthIntegration
from worklone_employee.tools.base import BaseTool

from worklone_employee.integrations.jira.add_attachment import JiraAddAttachmentTool
from worklone_employee.integrations.jira.add_comment import JiraAddCommentTool
from worklone_employee.integrations.jira.add_watcher import JiraAddWatcherTool
from worklone_employee.integrations.jira.add_worklog import JiraAddWorklogTool
from worklone_employee.integrations.jira.assign_issue import JiraAssignIssueTool
from worklone_employee.integrations.jira.bulk_read import JiraBulkReadTool
from worklone_employee.integrations.jira.create_issue_link import JiraCreateIssueLinkTool
from worklone_employee.integrations.jira.delete_attachment import JiraDeleteAttachmentTool
from worklone_employee.integrations.jira.delete_comment import JiraDeleteCommentTool
from worklone_employee.integrations.jira.delete_issue import JiraDeleteIssueTool
from worklone_employee.integrations.jira.delete_issue_link import JiraDeleteIssueLinkTool
from worklone_employee.integrations.jira.delete_worklog import JiraDeleteWorklogTool
from worklone_employee.integrations.jira.get_attachments import JiraGetAttachmentsTool
from worklone_employee.integrations.jira.get_comments import JiraGetCommentsTool
from worklone_employee.integrations.jira.get_users import JiraGetUsersTool
from worklone_employee.integrations.jira.remove_watcher import JiraRemoveWatcherTool
from worklone_employee.integrations.jira.retrieve import JiraRetrieveTool
from worklone_employee.integrations.jira.search_issues import JiraSearchIssuesTool
from worklone_employee.integrations.jira.transition_issue import JiraTransitionIssueTool
from worklone_employee.integrations.jira.update import JiraUpdateTool
from worklone_employee.integrations.jira.update_comment import JiraUpdateCommentTool
from worklone_employee.integrations.jira.update_worklog import JiraUpdateWorklogTool
from worklone_employee.integrations.jira.write import JiraWriteTool

_TOOL_CLASSES = [
    JiraAddAttachmentTool, JiraAddCommentTool, JiraAddWatcherTool, JiraAddWorklogTool, JiraAssignIssueTool, JiraBulkReadTool, JiraCreateIssueLinkTool, JiraDeleteAttachmentTool, JiraDeleteCommentTool, JiraDeleteIssueTool, JiraDeleteIssueLinkTool, JiraDeleteWorklogTool, JiraGetAttachmentsTool, JiraGetCommentsTool, JiraGetUsersTool, JiraRemoveWatcherTool, JiraRetrieveTool, JiraSearchIssuesTool, JiraTransitionIssueTool, JiraUpdateTool, JiraUpdateCommentTool, JiraUpdateWorklogTool, JiraWriteTool,
]

def _wire(tool: BaseTool, integration) -> BaseTool:
    async def _resolve_access_token(context=None):
        user_id = (context or {}).get("user_id") or (context or {}).get("owner_id")
        if not user_id:
            raise ValueError("user_id missing from context — pass user_id when calling emp.run()")
        return await integration._get_token(user_id)
    tool._resolve_access_token = _resolve_access_token
    return tool


class Jira(OAuthIntegration):
    PROVIDER = "jira"
    """Atlassian OAuth 2.0 (3LO)."""

    _AUTH_BASE = "https://auth.atlassian.com/authorize"
    _TOKEN_URL = "https://auth.atlassian.com/oauth/token"
    SCOPES = ['read:jira-user', 'read:jira-work', 'write:jira-work', 'offline_access']

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
    def add_attachment(self): return _wire(JiraAddAttachmentTool(), self)
    @property
    def add_comment(self): return _wire(JiraAddCommentTool(), self)
    @property
    def add_watcher(self): return _wire(JiraAddWatcherTool(), self)
    @property
    def add_worklog(self): return _wire(JiraAddWorklogTool(), self)
    @property
    def assign_issue(self): return _wire(JiraAssignIssueTool(), self)
    @property
    def bulk_read(self): return _wire(JiraBulkReadTool(), self)
    @property
    def create_issue_link(self): return _wire(JiraCreateIssueLinkTool(), self)
    @property
    def delete_attachment(self): return _wire(JiraDeleteAttachmentTool(), self)
    @property
    def delete_comment(self): return _wire(JiraDeleteCommentTool(), self)
    @property
    def delete_issue(self): return _wire(JiraDeleteIssueTool(), self)
    @property
    def delete_issue_link(self): return _wire(JiraDeleteIssueLinkTool(), self)
    @property
    def delete_worklog(self): return _wire(JiraDeleteWorklogTool(), self)
    @property
    def get_attachments(self): return _wire(JiraGetAttachmentsTool(), self)
    @property
    def get_comments(self): return _wire(JiraGetCommentsTool(), self)
    @property
    def get_users(self): return _wire(JiraGetUsersTool(), self)
    @property
    def remove_watcher(self): return _wire(JiraRemoveWatcherTool(), self)
    @property
    def retrieve(self): return _wire(JiraRetrieveTool(), self)
    @property
    def search_issues(self): return _wire(JiraSearchIssuesTool(), self)
    @property
    def transition_issue(self): return _wire(JiraTransitionIssueTool(), self)
    @property
    def update(self): return _wire(JiraUpdateTool(), self)
    @property
    def update_comment(self): return _wire(JiraUpdateCommentTool(), self)
    @property
    def update_worklog(self): return _wire(JiraUpdateWorklogTool(), self)
    @property
    def write(self): return _wire(JiraWriteTool(), self)
