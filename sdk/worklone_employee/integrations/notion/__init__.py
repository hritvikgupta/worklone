"""
Notion integration for worklone-employee SDK.
"""
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode
import httpx
from worklone_employee.integrations.base import ApiKeyIntegration
from worklone_employee.tools.base import BaseTool

from worklone_employee.integrations.notion.add_database_row import NotionAddDatabaseRowTool
from worklone_employee.integrations.notion.create_database import NotionCreateDatabaseTool
from worklone_employee.integrations.notion.create_page import NotionCreatePageTool
from worklone_employee.integrations.notion.query_database import NotionQueryDatabaseTool
from worklone_employee.integrations.notion.read import NotionReadTool
from worklone_employee.integrations.notion.read_database import NotionReadDatabaseTool
from worklone_employee.integrations.notion.search import NotionSearchTool
from worklone_employee.integrations.notion.update_page import NotionUpdatePageTool
from worklone_employee.integrations.notion.write import NotionWriteTool

_TOOL_CLASSES = [
    NotionAddDatabaseRowTool, NotionCreateDatabaseTool, NotionCreatePageTool, NotionQueryDatabaseTool, NotionReadTool, NotionReadDatabaseTool, NotionSearchTool, NotionUpdatePageTool, NotionWriteTool,
]

def _wire(tool: BaseTool, integration) -> BaseTool:
    async def _resolve_access_token(context=None):
        return integration._get_token()
    tool._resolve_access_token = _resolve_access_token
    return tool


class Notion(ApiKeyIntegration):
    """Pass a Notion integration token (secret_...) or OAuth access token."""

    def __init__(self, api_key: str):
        super().__init__(api_key)


    def all(self) -> List[BaseTool]:
        return [_wire(cls(), self) for cls in _TOOL_CLASSES]

    @property
    def add_database_row(self): return _wire(NotionAddDatabaseRowTool(), self)
    @property
    def create_database(self): return _wire(NotionCreateDatabaseTool(), self)
    @property
    def create_page(self): return _wire(NotionCreatePageTool(), self)
    @property
    def query_database(self): return _wire(NotionQueryDatabaseTool(), self)
    @property
    def read(self): return _wire(NotionReadTool(), self)
    @property
    def read_database(self): return _wire(NotionReadDatabaseTool(), self)
    @property
    def search(self): return _wire(NotionSearchTool(), self)
    @property
    def update_page(self): return _wire(NotionUpdatePageTool(), self)
    @property
    def write(self): return _wire(NotionWriteTool(), self)
