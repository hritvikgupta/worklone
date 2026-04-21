"""
Hubspot integration for worklone-employee SDK.
"""
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode
import httpx
from worklone_employee.integrations.base import OAuthIntegration, OAuthIntegration
from worklone_employee.tools.base import BaseTool

from worklone_employee.integrations.hubspot.create_appointment import HubspotCreateAppointmentTool
from worklone_employee.integrations.hubspot.create_company import HubspotCreateCompanyTool
from worklone_employee.integrations.hubspot.create_contact import HubspotCreateContactTool
from worklone_employee.integrations.hubspot.create_deal import HubspotCreateDealTool
from worklone_employee.integrations.hubspot.create_line_item import HubspotCreateLineItemTool
from worklone_employee.integrations.hubspot.create_list import HubspotCreateListTool
from worklone_employee.integrations.hubspot.create_ticket import HubspotCreateTicketTool
from worklone_employee.integrations.hubspot.get_appointment import HubspotGetAppointmentTool
from worklone_employee.integrations.hubspot.get_cart import HubspotGetCartTool
from worklone_employee.integrations.hubspot.get_company import HubspotGetCompanyTool
from worklone_employee.integrations.hubspot.get_contact import HubspotGetContactTool
from worklone_employee.integrations.hubspot.get_deal import HubspotGetDealTool
from worklone_employee.integrations.hubspot.get_line_item import HubspotGetLineItemTool
from worklone_employee.integrations.hubspot.get_list import HubspotGetListTool
from worklone_employee.integrations.hubspot.get_marketing_event import HubspotGetMarketingEventTool
from worklone_employee.integrations.hubspot.get_quote import HubspotGetQuoteTool
from worklone_employee.integrations.hubspot.get_ticket import HubspotGetTicketTool
from worklone_employee.integrations.hubspot.get_users import HubspotGetUsersTool
from worklone_employee.integrations.hubspot.list_appointments import HubspotListAppointmentsTool
from worklone_employee.integrations.hubspot.list_carts import HubspotListCartsTool
from worklone_employee.integrations.hubspot.list_companies import HubspotListCompaniesTool
from worklone_employee.integrations.hubspot.list_contacts import HubspotListContactsTool
from worklone_employee.integrations.hubspot.list_deals import HubspotListDealsTool
from worklone_employee.integrations.hubspot.list_line_items import HubspotListLineItemsTool
from worklone_employee.integrations.hubspot.list_lists import HubspotListListsTool
from worklone_employee.integrations.hubspot.list_marketing_events import HubspotListMarketingEventsTool
from worklone_employee.integrations.hubspot.list_owners import HubspotListOwnersTool
from worklone_employee.integrations.hubspot.list_quotes import HubspotListQuotesTool
from worklone_employee.integrations.hubspot.list_tickets import HubspotListTicketsTool
from worklone_employee.integrations.hubspot.search_companies import HubspotSearchCompaniesTool
from worklone_employee.integrations.hubspot.search_contacts import HubspotSearchContactsTool
from worklone_employee.integrations.hubspot.search_deals import HubspotSearchDealsTool
from worklone_employee.integrations.hubspot.search_tickets import HubspotSearchTicketsTool
from worklone_employee.integrations.hubspot.update_appointment import HubspotUpdateAppointmentTool
from worklone_employee.integrations.hubspot.update_company import HubspotUpdateCompanyTool
from worklone_employee.integrations.hubspot.update_contact import HubspotUpdateContactTool
from worklone_employee.integrations.hubspot.update_deal import HubspotUpdateDealTool
from worklone_employee.integrations.hubspot.update_line_item import HubspotUpdateLineItemTool
from worklone_employee.integrations.hubspot.update_ticket import HubspotUpdateTicketTool

_TOOL_CLASSES = [
    HubspotCreateAppointmentTool, HubspotCreateCompanyTool, HubspotCreateContactTool, HubspotCreateDealTool, HubspotCreateLineItemTool, HubspotCreateListTool, HubspotCreateTicketTool, HubspotGetAppointmentTool, HubspotGetCartTool, HubspotGetCompanyTool, HubspotGetContactTool, HubspotGetDealTool, HubspotGetLineItemTool, HubspotGetListTool, HubspotGetMarketingEventTool, HubspotGetQuoteTool, HubspotGetTicketTool, HubspotGetUsersTool, HubspotListAppointmentsTool, HubspotListCartsTool, HubspotListCompaniesTool, HubspotListContactsTool, HubspotListDealsTool, HubspotListLineItemsTool, HubspotListListsTool, HubspotListMarketingEventsTool, HubspotListOwnersTool, HubspotListQuotesTool, HubspotListTicketsTool, HubspotSearchCompaniesTool, HubspotSearchContactsTool, HubspotSearchDealsTool, HubspotSearchTicketsTool, HubspotUpdateAppointmentTool, HubspotUpdateCompanyTool, HubspotUpdateContactTool, HubspotUpdateDealTool, HubspotUpdateLineItemTool, HubspotUpdateTicketTool,
]

def _wire(tool: BaseTool, integration) -> BaseTool:
    async def _resolve_access_token(context=None):
        user_id = (context or {}).get("user_id") or (context or {}).get("owner_id")
        if not user_id:
            raise ValueError("user_id missing from context — pass user_id when calling emp.run()")
        return await integration._get_token(user_id)
    tool._resolve_access_token = _resolve_access_token
    return tool


class Hubspot(OAuthIntegration):
    PROVIDER = "hubspot"
    """HubSpot OAuth."""

    _AUTH_BASE = "https://app.hubspot.com/oauth/authorize"
    _TOKEN_URL = "https://api.hubapi.com/oauth/v1/token"
    SCOPES = ['crm.objects.contacts.read', 'crm.objects.contacts.write', 'crm.objects.deals.read', 'crm.objects.deals.write']

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
    def create_appointment(self): return _wire(HubspotCreateAppointmentTool(), self)
    @property
    def create_company(self): return _wire(HubspotCreateCompanyTool(), self)
    @property
    def create_contact(self): return _wire(HubspotCreateContactTool(), self)
    @property
    def create_deal(self): return _wire(HubspotCreateDealTool(), self)
    @property
    def create_line_item(self): return _wire(HubspotCreateLineItemTool(), self)
    @property
    def create_list(self): return _wire(HubspotCreateListTool(), self)
    @property
    def create_ticket(self): return _wire(HubspotCreateTicketTool(), self)
    @property
    def get_appointment(self): return _wire(HubspotGetAppointmentTool(), self)
    @property
    def get_cart(self): return _wire(HubspotGetCartTool(), self)
    @property
    def get_company(self): return _wire(HubspotGetCompanyTool(), self)
    @property
    def get_contact(self): return _wire(HubspotGetContactTool(), self)
    @property
    def get_deal(self): return _wire(HubspotGetDealTool(), self)
    @property
    def get_line_item(self): return _wire(HubspotGetLineItemTool(), self)
    @property
    def get_list(self): return _wire(HubspotGetListTool(), self)
    @property
    def get_marketing_event(self): return _wire(HubspotGetMarketingEventTool(), self)
    @property
    def get_quote(self): return _wire(HubspotGetQuoteTool(), self)
    @property
    def get_ticket(self): return _wire(HubspotGetTicketTool(), self)
    @property
    def get_users(self): return _wire(HubspotGetUsersTool(), self)
    @property
    def list_appointments(self): return _wire(HubspotListAppointmentsTool(), self)
    @property
    def list_carts(self): return _wire(HubspotListCartsTool(), self)
    @property
    def list_companies(self): return _wire(HubspotListCompaniesTool(), self)
    @property
    def list_contacts(self): return _wire(HubspotListContactsTool(), self)
    @property
    def list_deals(self): return _wire(HubspotListDealsTool(), self)
    @property
    def list_line_items(self): return _wire(HubspotListLineItemsTool(), self)
    @property
    def list_lists(self): return _wire(HubspotListListsTool(), self)
    @property
    def list_marketing_events(self): return _wire(HubspotListMarketingEventsTool(), self)
    @property
    def list_owners(self): return _wire(HubspotListOwnersTool(), self)
    @property
    def list_quotes(self): return _wire(HubspotListQuotesTool(), self)
    @property
    def list_tickets(self): return _wire(HubspotListTicketsTool(), self)
    @property
    def search_companies(self): return _wire(HubspotSearchCompaniesTool(), self)
    @property
    def search_contacts(self): return _wire(HubspotSearchContactsTool(), self)
    @property
    def search_deals(self): return _wire(HubspotSearchDealsTool(), self)
    @property
    def search_tickets(self): return _wire(HubspotSearchTicketsTool(), self)
    @property
    def update_appointment(self): return _wire(HubspotUpdateAppointmentTool(), self)
    @property
    def update_company(self): return _wire(HubspotUpdateCompanyTool(), self)
    @property
    def update_contact(self): return _wire(HubspotUpdateContactTool(), self)
    @property
    def update_deal(self): return _wire(HubspotUpdateDealTool(), self)
    @property
    def update_line_item(self): return _wire(HubspotUpdateLineItemTool(), self)
    @property
    def update_ticket(self): return _wire(HubspotUpdateTicketTool(), self)
