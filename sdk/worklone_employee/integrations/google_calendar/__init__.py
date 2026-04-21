"""
GoogleCalendar integration for worklone-employee SDK.
"""
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode
import httpx
from worklone_employee.integrations.base import GoogleOAuthIntegration, OAuthIntegration
from worklone_employee.tools.base import BaseTool

from worklone_employee.integrations.google_calendar.create import GoogleCalendarCreateTool
from worklone_employee.integrations.google_calendar.delete import GoogleCalendarDeleteTool
from worklone_employee.integrations.google_calendar.freebusy import GoogleCalendarFreebusyTool
from worklone_employee.integrations.google_calendar.get import GoogleCalendarGetTool
from worklone_employee.integrations.google_calendar.instances import GoogleCalendarInstancesTool
from worklone_employee.integrations.google_calendar.invite import GoogleCalendarInviteTool
from worklone_employee.integrations.google_calendar.list import GoogleCalendarListTool
from worklone_employee.integrations.google_calendar.list_calendars import GoogleCalendarListCalendarsTool
from worklone_employee.integrations.google_calendar.move import GoogleCalendarMoveTool
from worklone_employee.integrations.google_calendar.quick_add import GoogleCalendarQuickAddTool
from worklone_employee.integrations.google_calendar.update import GoogleCalendarUpdateTool

_TOOL_CLASSES = [
    GoogleCalendarCreateTool, GoogleCalendarDeleteTool, GoogleCalendarFreebusyTool, GoogleCalendarGetTool, GoogleCalendarInstancesTool, GoogleCalendarInviteTool, GoogleCalendarListTool, GoogleCalendarListCalendarsTool, GoogleCalendarMoveTool, GoogleCalendarQuickAddTool, GoogleCalendarUpdateTool,
]

def _wire(tool: BaseTool, integration) -> BaseTool:
    async def _resolve_access_token(context=None):
        user_id = (context or {}).get("user_id") or (context or {}).get("owner_id")
        if not user_id:
            raise ValueError("user_id missing from context — pass user_id when calling emp.run()")
        return await integration._get_token(user_id)
    tool._resolve_access_token = _resolve_access_token
    return tool


class GoogleCalendar(GoogleOAuthIntegration):
    PROVIDER = "google_calendar"

    SCOPES = ['https://www.googleapis.com/auth/calendar']

    def __init__(self, client_id: str, client_secret: str, token_store: "TokenStore"):
        super().__init__(client_id, client_secret, token_store)


    def all(self) -> List[BaseTool]:
        return [_wire(cls(), self) for cls in _TOOL_CLASSES]

    @property
    def create(self): return _wire(GoogleCalendarCreateTool(), self)
    @property
    def delete(self): return _wire(GoogleCalendarDeleteTool(), self)
    @property
    def freebusy(self): return _wire(GoogleCalendarFreebusyTool(), self)
    @property
    def get(self): return _wire(GoogleCalendarGetTool(), self)
    @property
    def instances(self): return _wire(GoogleCalendarInstancesTool(), self)
    @property
    def invite(self): return _wire(GoogleCalendarInviteTool(), self)
    @property
    def list(self): return _wire(GoogleCalendarListTool(), self)
    @property
    def list_calendars(self): return _wire(GoogleCalendarListCalendarsTool(), self)
    @property
    def move(self): return _wire(GoogleCalendarMoveTool(), self)
    @property
    def quick_add(self): return _wire(GoogleCalendarQuickAddTool(), self)
    @property
    def update(self): return _wire(GoogleCalendarUpdateTool(), self)
