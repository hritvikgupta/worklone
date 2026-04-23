from typing import Any, Dict
import httpx
import base64
import os
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GongListWorkspacesTool(BaseTool):
    name = "gong_list_workspaces"
    description = "List all company workspaces in Gong."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="gong_access_key",
                description="Gong API Access Key",
                env_var="GONG_ACCESS_KEY",
                required=True,
                auth_type="api_key",
            ),
            CredentialRequirement(
                key="gong_access_key_secret",
                description="Gong API Access Key Secret",
                env_var="GONG_ACCESS_KEY_SECRET",
                required=True,
                auth_type="api_key",
            ),
        ]

    def _get_gong_access_key(self, context: dict | None) -> str:
        token = context.get("gong_access_key") if context else ""
        if self._is_placeholder_token(token):
            token = os.environ.get("GONG_ACCESS_KEY", "")
        return token

    def _get_gong_access_key_secret(self, context: dict | None) -> str:
        token = context.get("gong_access_key_secret") if context else ""
        if self._is_placeholder_token(token):
            token = os.environ.get("GONG_ACCESS_KEY_SECRET", "")
        return token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {},
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_key = self._get_gong_access_key(context)
        access_key_secret = self._get_gong_access_key_secret(context)
        
        if self._is_placeholder_token(access_key) or self._is_placeholder_token(access_key_secret):
            return ToolResult(success=False, output="", error="Gong credentials not configured.")
        
        credentials = f"{access_key}:{access_key_secret}"
        auth_header = f"Basic {base64.b64encode(credentials.encode('utf-8')).decode('utf-8')}"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": auth_header,
        }
        
        url = "https://api.gong.io/v2/workspaces"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    workspaces = []
                    if "workspaces" in data:
                        for w in data["workspaces"]:
                            workspaces.append({
                                "id": w.get("id", ""),
                                "name": w.get("name"),
                                "description": w.get("description"),
                            })
                    return ToolResult(success=True, output=response.text, data={"workspaces": workspaces})
                else:
                    error_msg = response.text
                    try:
                        err_data = response.json()
                        if "errors" in err_data and err_data["errors"]:
                            error_msg = err_data["errors"][0].get("message", error_msg)
                        elif "message" in err_data:
                            error_msg = err_data["message"]
                    except:
                        pass
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")