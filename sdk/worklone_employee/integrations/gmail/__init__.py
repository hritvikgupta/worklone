"""
Gmail integration for worklone-employee SDK.

Usage:
    from worklone_employee.integrations import Gmail

    gmail = Gmail(
        client_id="xxx.apps.googleusercontent.com",
        client_secret="GOCSPX-xxx",
        access_token=db.get(user_id, "access_token"),
        refresh_token=db.get(user_id, "refresh_token"),
        on_token_refresh=lambda t: db.save(user_id, t),
    )
    emp.add_tools(gmail.all())

First-time OAuth:
    url = Gmail.get_auth_url(client_id, client_secret, redirect_uri)
    tokens = await Gmail.exchange_code(code, client_id, client_secret, redirect_uri)
"""

from typing import List
from worklone_employee.integrations.base import TokenStore, GoogleOAuthIntegration
from worklone_employee.tools.base import BaseTool

from worklone_employee.integrations.gmail.send import GmailSendTool
from worklone_employee.integrations.gmail.read import GmailReadTool
from worklone_employee.integrations.gmail.search import GmailSearchTool
from worklone_employee.integrations.gmail.draft import GmailDraftTool
from worklone_employee.integrations.gmail.list_threads import GmailListThreadsTool
from worklone_employee.integrations.gmail.list_labels import GmailListLabelsTool
from worklone_employee.integrations.gmail.mark_read import GmailMarkReadTool
from worklone_employee.integrations.gmail.mark_unread import GmailMarkUnreadTool
from worklone_employee.integrations.gmail.archive import GmailArchiveTool
from worklone_employee.integrations.gmail.unarchive import GmailUnarchiveTool
from worklone_employee.integrations.gmail.delete import GmailDeleteTool
from worklone_employee.integrations.gmail.add_label import GmailAddLabelTool
from worklone_employee.integrations.gmail.remove_label import GmailRemoveLabelTool
from worklone_employee.integrations.gmail.move import GmailMoveTool
from worklone_employee.integrations.gmail.get_thread import GmailGetThreadTool
from worklone_employee.integrations.gmail.trash_thread import GmailTrashThreadTool
from worklone_employee.integrations.gmail.get_draft import GmailGetDraftTool
from worklone_employee.integrations.gmail.list_drafts import GmailListDraftsTool
from worklone_employee.integrations.gmail.delete_draft import GmailDeleteDraftTool
from worklone_employee.integrations.gmail.create_label import GmailCreateLabelTool
from worklone_employee.integrations.gmail.delete_label import GmailDeleteLabelTool
from worklone_employee.integrations.gmail.untrash_thread import GmailUntrashThreadTool


_TOOL_CLASSES = [
    GmailSendTool, GmailReadTool, GmailSearchTool, GmailDraftTool,
    GmailListThreadsTool, GmailListLabelsTool, GmailMarkReadTool,
    GmailMarkUnreadTool, GmailArchiveTool, GmailUnarchiveTool,
    GmailDeleteTool, GmailAddLabelTool, GmailRemoveLabelTool,
    GmailMoveTool, GmailGetThreadTool, GmailTrashThreadTool,
    GmailGetDraftTool, GmailListDraftsTool, GmailDeleteDraftTool,
    GmailCreateLabelTool, GmailDeleteLabelTool, GmailUntrashThreadTool,
]


def _wire(tool: BaseTool, integration) -> BaseTool:
    async def _resolve_access_token(context=None):
        user_id = (context or {}).get("user_id") or (context or {}).get("owner_id")
        if not user_id:
            raise ValueError("user_id missing from context — pass user_id when calling emp.run()")
        return await integration._get_token(user_id)
    tool._resolve_access_token = _resolve_access_token
    return tool


class Gmail(GoogleOAuthIntegration):
    PROVIDER = "gmail"
    """Gmail integration — all 22 Gmail tools pre-wired to per-user tokens."""

    SCOPES = ["https://mail.google.com/"]

    def all(self) -> List[BaseTool]:
        return [_wire(cls(), self) for cls in _TOOL_CLASSES]

    # ── individual tool accessors ──────────────────────────────────────────────
    @property
    def send(self): return _wire(GmailSendTool(), self)
    @property
    def read(self): return _wire(GmailReadTool(), self)
    @property
    def search(self): return _wire(GmailSearchTool(), self)
    @property
    def draft(self): return _wire(GmailDraftTool(), self)
    @property
    def list_threads(self): return _wire(GmailListThreadsTool(), self)
    @property
    def list_labels(self): return _wire(GmailListLabelsTool(), self)
    @property
    def mark_read(self): return _wire(GmailMarkReadTool(), self)
    @property
    def mark_unread(self): return _wire(GmailMarkUnreadTool(), self)
    @property
    def archive(self): return _wire(GmailArchiveTool(), self)
    @property
    def unarchive(self): return _wire(GmailUnarchiveTool(), self)
    @property
    def delete(self): return _wire(GmailDeleteTool(), self)
    @property
    def add_label(self): return _wire(GmailAddLabelTool(), self)
    @property
    def remove_label(self): return _wire(GmailRemoveLabelTool(), self)
    @property
    def move(self): return _wire(GmailMoveTool(), self)
    @property
    def get_thread(self): return _wire(GmailGetThreadTool(), self)
    @property
    def trash_thread(self): return _wire(GmailTrashThreadTool(), self)
    @property
    def get_draft(self): return _wire(GmailGetDraftTool(), self)
    @property
    def list_drafts(self): return _wire(GmailListDraftsTool(), self)
    @property
    def delete_draft(self): return _wire(GmailDeleteDraftTool(), self)
    @property
    def create_label(self): return _wire(GmailCreateLabelTool(), self)
    @property
    def delete_label(self): return _wire(GmailDeleteLabelTool(), self)
    @property
    def untrash_thread(self): return _wire(GmailUntrashThreadTool(), self)
