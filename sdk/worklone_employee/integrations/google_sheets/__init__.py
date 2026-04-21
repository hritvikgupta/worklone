"""
GoogleSheets integration for worklone-employee SDK.
"""
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode
import httpx
from worklone_employee.integrations.base import GoogleOAuthIntegration, OAuthIntegration
from worklone_employee.tools.base import BaseTool

from worklone_employee.integrations.google_sheets.append import GoogleSheetsAppendTool
from worklone_employee.integrations.google_sheets.batch_clear import GoogleSheetsBatchClearTool
from worklone_employee.integrations.google_sheets.batch_get import GoogleSheetsBatchGetTool
from worklone_employee.integrations.google_sheets.batch_update import GoogleSheetsBatchUpdateTool
from worklone_employee.integrations.google_sheets.clear import GoogleSheetsClearTool
from worklone_employee.integrations.google_sheets.copy_sheet import GoogleSheetsCopySheetTool
from worklone_employee.integrations.google_sheets.create_spreadsheet import GoogleSheetsCreateSpreadsheetTool
from worklone_employee.integrations.google_sheets.delete_rows import GoogleSheetsDeleteRowsTool
from worklone_employee.integrations.google_sheets.delete_sheet import GoogleSheetsDeleteSheetTool
from worklone_employee.integrations.google_sheets.delete_spreadsheet import GoogleSheetsDeleteSpreadsheetTool
from worklone_employee.integrations.google_sheets.get_spreadsheet import GoogleSheetsGetSpreadsheetTool
from worklone_employee.integrations.google_sheets.read import GoogleSheetsReadTool
from worklone_employee.integrations.google_sheets.update import GoogleSheetsUpdateTool
from worklone_employee.integrations.google_sheets.write import GoogleSheetsWriteTool

_TOOL_CLASSES = [
    GoogleSheetsAppendTool, GoogleSheetsBatchClearTool, GoogleSheetsBatchGetTool, GoogleSheetsBatchUpdateTool, GoogleSheetsClearTool, GoogleSheetsCopySheetTool, GoogleSheetsCreateSpreadsheetTool, GoogleSheetsDeleteRowsTool, GoogleSheetsDeleteSheetTool, GoogleSheetsDeleteSpreadsheetTool, GoogleSheetsGetSpreadsheetTool, GoogleSheetsReadTool, GoogleSheetsUpdateTool, GoogleSheetsWriteTool,
]

def _wire(tool: BaseTool, integration) -> BaseTool:
    async def _resolve_access_token(context=None):
        user_id = (context or {}).get("user_id") or (context or {}).get("owner_id")
        if not user_id:
            raise ValueError("user_id missing from context — pass user_id when calling emp.run()")
        return await integration._get_token(user_id)
    tool._resolve_access_token = _resolve_access_token
    return tool


class GoogleSheets(GoogleOAuthIntegration):
    PROVIDER = "google_sheets"

    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

    def __init__(self, client_id: str, client_secret: str, token_store: "TokenStore"):
        super().__init__(client_id, client_secret, token_store)


    def all(self) -> List[BaseTool]:
        return [_wire(cls(), self) for cls in _TOOL_CLASSES]

    @property
    def append(self): return _wire(GoogleSheetsAppendTool(), self)
    @property
    def batch_clear(self): return _wire(GoogleSheetsBatchClearTool(), self)
    @property
    def batch_get(self): return _wire(GoogleSheetsBatchGetTool(), self)
    @property
    def batch_update(self): return _wire(GoogleSheetsBatchUpdateTool(), self)
    @property
    def clear(self): return _wire(GoogleSheetsClearTool(), self)
    @property
    def copy_sheet(self): return _wire(GoogleSheetsCopySheetTool(), self)
    @property
    def create_spreadsheet(self): return _wire(GoogleSheetsCreateSpreadsheetTool(), self)
    @property
    def delete_rows(self): return _wire(GoogleSheetsDeleteRowsTool(), self)
    @property
    def delete_sheet(self): return _wire(GoogleSheetsDeleteSheetTool(), self)
    @property
    def delete_spreadsheet(self): return _wire(GoogleSheetsDeleteSpreadsheetTool(), self)
    @property
    def get_spreadsheet(self): return _wire(GoogleSheetsGetSpreadsheetTool(), self)
    @property
    def read(self): return _wire(GoogleSheetsReadTool(), self)
    @property
    def update(self): return _wire(GoogleSheetsUpdateTool(), self)
    @property
    def write(self): return _wire(GoogleSheetsWriteTool(), self)
