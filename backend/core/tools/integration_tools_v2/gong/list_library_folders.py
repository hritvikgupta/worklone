from typing import Any, Dict, List, Optional, Tuple
import httpx
import base64
import json
from os import getenv
from urllib.parse import urlencode
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GongListLibraryFoldersTool(BaseTool):
    name = "Gong List Library Folders"
    description = "Retrieve library folders from Gong."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="accessKey",
                description="Gong API Access Key",
                env_var="GONG_ACCESS_KEY",
                required=True,
                auth_type="api_key",
            ),
            CredentialRequirement(
                key="accessKeySecret",
                description="Gong API Access Key Secret",
                env_var="GONG_ACCESS_KEY_SECRET",
                required=True,
                auth_type="api_key",
            ),
        ]

    def _get_credentials(self, context: dict | None) -> Tuple[Optional[str], Optional[str]]:
        access_key = (context or {}).get("accessKey")
        access_key_secret = (context or {}).get("accessKeySecret")
        if self._is_placeholder_token(access_key or ""):
            access_key = getenv("GONG_ACCESS_KEY")
        if self._is_placeholder_token(access_key_secret or ""):
            access_key_secret = getenv("GONG_ACCESS_KEY_SECRET")
        return access_key, access_key_secret

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "workspaceId": {
                    "type": "string",
                    "description": "Gong workspace ID to filter folders",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_key, access_key_secret = self._get_credentials(context)
        
        if self._is_placeholder_token(access_key or "") or self._is_placeholder_token(access_key_secret or ""):
            return ToolResult(success=False, output="", error="Gong access credentials not configured.")
        
        workspace_id = parameters.get("workspaceId")
        query_params: Dict[str, str] = {}
        if workspace_id:
            query_params["workspaceId"] = str(workspace_id)
        
        url = "https://api.gong.io/v2/library/folders"
        if query_params:
            url += "?" + urlencode(query_params)
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {base64.b64encode(f'{access_key}:{access_key_secret}'.encode('utf-8')).decode('utf-8')}",
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code != 200:
                    try:
                        error_data = response.json()
                        error_msg = (
                            error_data.get("errors", [{}])[0].get("message")
                            or error_data.get("message")
                            or response.text
                        )
                    except Exception:
                        error_msg = response.text or "Failed to list library folders"
                    return ToolResult(success=False, output="", error=error_msg)
                
                data = response.json()
                folders = [
                    {
                        "id": f.get("id") or "",
                        "name": f.get("name") or "",
                        "parentFolderId": f.get("parentFolderId"),
                        "createdBy": f.get("createdBy"),
                        "updated": f.get("updated"),
                    }
                    for f in data.get("folders", [])
                ]
                output_data = {"folders": folders}
                return ToolResult(
                    success=True,
                    output=json.dumps(output_data),
                    data=output_data,
                )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")