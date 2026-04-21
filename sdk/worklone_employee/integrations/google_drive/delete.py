from typing import Any, Dict
import httpx
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class GoogleDriveDeleteTool(BaseTool):
    name = "google_drive_delete"
    description = "Permanently delete a file from Google Drive (bypasses trash)"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GOOGLE_DRIVE_ACCESS_TOKEN",
                description="Access token",
                env_var="GOOGLE_DRIVE_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "google-drive",
            context=context,
            context_token_keys=("access_token",),
            env_token_keys=("GOOGLE_DRIVE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "fileId": {
                    "type": "string",
                    "description": "The ID of the file to permanently delete",
                }
            },
            "required": ["fileId"],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        file_id = (parameters.get("fileId") or "").strip()
        if not file_id:
            return ToolResult(success=False, output="", error="fileId is required.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        
        url = f"https://www.googleapis.com/drive/v3/files/{file_id}?supportsAllDrives=true"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)
                
                if response.status_code in [200, 204]:
                    data = {
                        "deleted": True,
                        "fileId": file_id,
                    }
                    return ToolResult(success=True, output="", data=data)
                else:
                    error_msg = response.text
                    try:
                        error_data = response.json()
                        if isinstance(error_data, dict):
                            error = error_data.get("error")
                            if isinstance(error, dict):
                                error_msg = error.get("message", response.text)
                            else:
                                error_msg = str(error_data)
                    except ValueError:
                        pass
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")