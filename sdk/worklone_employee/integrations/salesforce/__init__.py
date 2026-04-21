"""
Salesforce integration for worklone-employee SDK.
"""
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode
import httpx
from worklone_employee.integrations.base import TokenStore, OAuthIntegration, OAuthIntegration
from worklone_employee.tools.base import BaseTool

from worklone_employee.integrations.salesforce.create_account import SalesforceCreateAccountTool
from worklone_employee.integrations.salesforce.create_case import SalesforceCreateCaseTool
from worklone_employee.integrations.salesforce.create_contact import SalesforceCreateContactTool
from worklone_employee.integrations.salesforce.create_lead import SalesforceCreateLeadTool
from worklone_employee.integrations.salesforce.create_opportunity import SalesforceCreateOpportunityTool
from worklone_employee.integrations.salesforce.create_task import SalesforceCreateTaskTool
from worklone_employee.integrations.salesforce.delete_account import SalesforceDeleteAccountTool
from worklone_employee.integrations.salesforce.delete_case import SalesforceDeleteCaseTool
from worklone_employee.integrations.salesforce.delete_contact import SalesforceDeleteContactTool
from worklone_employee.integrations.salesforce.delete_lead import SalesforceDeleteLeadTool
from worklone_employee.integrations.salesforce.delete_opportunity import SalesforceDeleteOpportunityTool
from worklone_employee.integrations.salesforce.delete_task import SalesforceDeleteTaskTool
from worklone_employee.integrations.salesforce.describe_object import SalesforceDescribeObjectTool
from worklone_employee.integrations.salesforce.get_accounts import SalesforceGetAccountsTool
from worklone_employee.integrations.salesforce.get_cases import SalesforceGetCasesTool
from worklone_employee.integrations.salesforce.get_contacts import SalesforceGetContactsTool
from worklone_employee.integrations.salesforce.get_dashboard import SalesforceGetDashboardTool
from worklone_employee.integrations.salesforce.get_leads import SalesforceGetLeadsTool
from worklone_employee.integrations.salesforce.get_opportunities import SalesforceGetOpportunitiesTool
from worklone_employee.integrations.salesforce.get_report import SalesforceGetReportTool
from worklone_employee.integrations.salesforce.get_tasks import SalesforceGetTasksTool
from worklone_employee.integrations.salesforce.list_dashboards import SalesforceListDashboardsTool
from worklone_employee.integrations.salesforce.list_objects import SalesforceListObjectsTool
from worklone_employee.integrations.salesforce.list_report_types import SalesforceListReportTypesTool
from worklone_employee.integrations.salesforce.list_reports import SalesforceListReportsTool
from worklone_employee.integrations.salesforce.query import SalesforceQueryTool
from worklone_employee.integrations.salesforce.query_more import SalesforceQueryMoreTool
from worklone_employee.integrations.salesforce.refresh_dashboard import SalesforceRefreshDashboardTool
from worklone_employee.integrations.salesforce.run_report import SalesforceRunReportTool
from worklone_employee.integrations.salesforce.update_account import SalesforceUpdateAccountTool
from worklone_employee.integrations.salesforce.update_case import SalesforceUpdateCaseTool
from worklone_employee.integrations.salesforce.update_contact import SalesforceUpdateContactTool
from worklone_employee.integrations.salesforce.update_lead import SalesforceUpdateLeadTool
from worklone_employee.integrations.salesforce.update_opportunity import SalesforceUpdateOpportunityTool
from worklone_employee.integrations.salesforce.update_task import SalesforceUpdateTaskTool

_TOOL_CLASSES = [
    SalesforceCreateAccountTool, SalesforceCreateCaseTool, SalesforceCreateContactTool, SalesforceCreateLeadTool, SalesforceCreateOpportunityTool, SalesforceCreateTaskTool, SalesforceDeleteAccountTool, SalesforceDeleteCaseTool, SalesforceDeleteContactTool, SalesforceDeleteLeadTool, SalesforceDeleteOpportunityTool, SalesforceDeleteTaskTool, SalesforceDescribeObjectTool, SalesforceGetAccountsTool, SalesforceGetCasesTool, SalesforceGetContactsTool, SalesforceGetDashboardTool, SalesforceGetLeadsTool, SalesforceGetOpportunitiesTool, SalesforceGetReportTool, SalesforceGetTasksTool, SalesforceListDashboardsTool, SalesforceListObjectsTool, SalesforceListReportTypesTool, SalesforceListReportsTool, SalesforceQueryTool, SalesforceQueryMoreTool, SalesforceRefreshDashboardTool, SalesforceRunReportTool, SalesforceUpdateAccountTool, SalesforceUpdateCaseTool, SalesforceUpdateContactTool, SalesforceUpdateLeadTool, SalesforceUpdateOpportunityTool, SalesforceUpdateTaskTool,
]

def _wire(tool: BaseTool, integration) -> BaseTool:
    async def _resolve_access_token(context=None):
        user_id = (context or {}).get("user_id") or (context or {}).get("owner_id")
        if not user_id:
            raise ValueError("user_id missing from context")
        return await integration._get_token(user_id)
    async def _resolve_connection(context=None):
        user_id = (context or {}).get("user_id") or (context or {}).get("owner_id")
        if not user_id:
            raise ValueError("user_id missing from context")
        tokens = await integration._store.get(user_id, integration.PROVIDER)
        if not tokens:
            raise ValueError(f"No tokens for user {user_id}")
        class _Conn:
            pass
        conn = _Conn()
        conn.access_token = tokens["access_token"]
        conn.instance_url = tokens.get("instance_url", "")
        return conn
    tool._resolve_access_token = _resolve_access_token
    tool._resolve_connection = _resolve_connection
    return tool


class Salesforce(OAuthIntegration):
    PROVIDER = "salesforce"
    """Salesforce Connected App OAuth."""

    _AUTH_BASE = "https://login.salesforce.com/services/oauth2/authorize"
    _TOKEN_URL = "https://login.salesforce.com/services/oauth2/token"
    SCOPES = ['api', 'refresh_token', 'offline_access']

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
    def create_account(self): return _wire(SalesforceCreateAccountTool(), self)
    @property
    def create_case(self): return _wire(SalesforceCreateCaseTool(), self)
    @property
    def create_contact(self): return _wire(SalesforceCreateContactTool(), self)
    @property
    def create_lead(self): return _wire(SalesforceCreateLeadTool(), self)
    @property
    def create_opportunity(self): return _wire(SalesforceCreateOpportunityTool(), self)
    @property
    def create_task(self): return _wire(SalesforceCreateTaskTool(), self)
    @property
    def delete_account(self): return _wire(SalesforceDeleteAccountTool(), self)
    @property
    def delete_case(self): return _wire(SalesforceDeleteCaseTool(), self)
    @property
    def delete_contact(self): return _wire(SalesforceDeleteContactTool(), self)
    @property
    def delete_lead(self): return _wire(SalesforceDeleteLeadTool(), self)
    @property
    def delete_opportunity(self): return _wire(SalesforceDeleteOpportunityTool(), self)
    @property
    def delete_task(self): return _wire(SalesforceDeleteTaskTool(), self)
    @property
    def describe_object(self): return _wire(SalesforceDescribeObjectTool(), self)
    @property
    def get_accounts(self): return _wire(SalesforceGetAccountsTool(), self)
    @property
    def get_cases(self): return _wire(SalesforceGetCasesTool(), self)
    @property
    def get_contacts(self): return _wire(SalesforceGetContactsTool(), self)
    @property
    def get_dashboard(self): return _wire(SalesforceGetDashboardTool(), self)
    @property
    def get_leads(self): return _wire(SalesforceGetLeadsTool(), self)
    @property
    def get_opportunities(self): return _wire(SalesforceGetOpportunitiesTool(), self)
    @property
    def get_report(self): return _wire(SalesforceGetReportTool(), self)
    @property
    def get_tasks(self): return _wire(SalesforceGetTasksTool(), self)
    @property
    def list_dashboards(self): return _wire(SalesforceListDashboardsTool(), self)
    @property
    def list_objects(self): return _wire(SalesforceListObjectsTool(), self)
    @property
    def list_report_types(self): return _wire(SalesforceListReportTypesTool(), self)
    @property
    def list_reports(self): return _wire(SalesforceListReportsTool(), self)
    @property
    def query(self): return _wire(SalesforceQueryTool(), self)
    @property
    def query_more(self): return _wire(SalesforceQueryMoreTool(), self)
    @property
    def refresh_dashboard(self): return _wire(SalesforceRefreshDashboardTool(), self)
    @property
    def run_report(self): return _wire(SalesforceRunReportTool(), self)
    @property
    def update_account(self): return _wire(SalesforceUpdateAccountTool(), self)
    @property
    def update_case(self): return _wire(SalesforceUpdateCaseTool(), self)
    @property
    def update_contact(self): return _wire(SalesforceUpdateContactTool(), self)
    @property
    def update_lead(self): return _wire(SalesforceUpdateLeadTool(), self)
    @property
    def update_opportunity(self): return _wire(SalesforceUpdateOpportunityTool(), self)
    @property
    def update_task(self): return _wire(SalesforceUpdateTaskTool(), self)
