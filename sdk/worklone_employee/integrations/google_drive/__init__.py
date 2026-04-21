"""
GoogleDrive integration for worklone-employee SDK.
"""
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode
import httpx
from worklone_employee.integrations.base import GoogleOAuthIntegration, OAuthIntegration
from worklone_employee.tools.base import BaseTool

from worklone_employee.integrations.google_drive.copy import GoogleDriveCopyTool
from worklone_employee.integrations.google_drive.create_folder import GoogleDriveCreateFolderTool
from worklone_employee.integrations.google_drive.delete import GoogleDriveDeleteTool
from worklone_employee.integrations.google_drive.download import GoogleDriveDownloadTool
from worklone_employee.integrations.google_drive.get_about import GoogleDriveGetAboutTool
from worklone_employee.integrations.google_drive.get_content import GoogleDriveGetContentTool
from worklone_employee.integrations.google_drive.get_file import GoogleDriveGetFileTool
from worklone_employee.integrations.google_drive.list import GoogleDriveListTool
from worklone_employee.integrations.google_drive.list_permissions import GoogleDriveListPermissionsTool
from worklone_employee.integrations.google_drive.move import GoogleDriveMoveTool
from worklone_employee.integrations.google_drive.search import GoogleDriveSearchTool
from worklone_employee.integrations.google_drive.share import GoogleDriveShareTool
from worklone_employee.integrations.google_drive.trash import GoogleDriveTrashTool
from worklone_employee.integrations.google_drive.unshare import GoogleDriveUnshareTool
from worklone_employee.integrations.google_drive.untrash import GoogleDriveUntrashTool
from worklone_employee.integrations.google_drive.update import GoogleDriveUpdateTool
from worklone_employee.integrations.google_drive.upload import GoogleDriveUploadTool

_TOOL_CLASSES = [
    GoogleDriveCopyTool, GoogleDriveCreateFolderTool, GoogleDriveDeleteTool, GoogleDriveDownloadTool, GoogleDriveGetAboutTool, GoogleDriveGetContentTool, GoogleDriveGetFileTool, GoogleDriveListTool, GoogleDriveListPermissionsTool, GoogleDriveMoveTool, GoogleDriveSearchTool, GoogleDriveShareTool, GoogleDriveTrashTool, GoogleDriveUnshareTool, GoogleDriveUntrashTool, GoogleDriveUpdateTool, GoogleDriveUploadTool,
]

def _wire(tool: BaseTool, integration) -> BaseTool:
    async def _resolve_access_token(context=None):
        user_id = (context or {}).get("user_id") or (context or {}).get("owner_id")
        if not user_id:
            raise ValueError("user_id missing from context — pass user_id when calling emp.run()")
        return await integration._get_token(user_id)
    tool._resolve_access_token = _resolve_access_token
    return tool


class GoogleDrive(GoogleOAuthIntegration):
    PROVIDER = "google_drive"

    SCOPES = ['https://www.googleapis.com/auth/drive']

    def __init__(self, client_id: str, client_secret: str, token_store: "TokenStore"):
        super().__init__(client_id, client_secret, token_store)


    def all(self) -> List[BaseTool]:
        return [_wire(cls(), self) for cls in _TOOL_CLASSES]

    @property
    def copy(self): return _wire(GoogleDriveCopyTool(), self)
    @property
    def create_folder(self): return _wire(GoogleDriveCreateFolderTool(), self)
    @property
    def delete(self): return _wire(GoogleDriveDeleteTool(), self)
    @property
    def download(self): return _wire(GoogleDriveDownloadTool(), self)
    @property
    def get_about(self): return _wire(GoogleDriveGetAboutTool(), self)
    @property
    def get_content(self): return _wire(GoogleDriveGetContentTool(), self)
    @property
    def get_file(self): return _wire(GoogleDriveGetFileTool(), self)
    @property
    def list(self): return _wire(GoogleDriveListTool(), self)
    @property
    def list_permissions(self): return _wire(GoogleDriveListPermissionsTool(), self)
    @property
    def move(self): return _wire(GoogleDriveMoveTool(), self)
    @property
    def search(self): return _wire(GoogleDriveSearchTool(), self)
    @property
    def share(self): return _wire(GoogleDriveShareTool(), self)
    @property
    def trash(self): return _wire(GoogleDriveTrashTool(), self)
    @property
    def unshare(self): return _wire(GoogleDriveUnshareTool(), self)
    @property
    def untrash(self): return _wire(GoogleDriveUntrashTool(), self)
    @property
    def update(self): return _wire(GoogleDriveUpdateTool(), self)
    @property
    def upload(self): return _wire(GoogleDriveUploadTool(), self)
