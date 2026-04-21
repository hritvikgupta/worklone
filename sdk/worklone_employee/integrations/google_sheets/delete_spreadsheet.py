from typing import Any, Dict
import httpx
import json
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class GoogleSheetsDeleteSpreadsheetTool(BaseTool):
    name = "google_sheets_delete_spreadsheet"
    description = "Permanently delete a Google Sheets spreadsheet using the Google Drive API"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GOOGLE_SHEETS_ACCESS_TOKEN",
                description="Access token for the Google Sheets API",
                env_var="GOOGLE_SHEETS_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "google-sheets",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("GOOGLE_SHEETS_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "spreadsheetId": {
                    "type": "string",
                    "description": "The ID of the Google Sheets spreadsheet to delete",
                },
            },
            "required": ["spreadsheetId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        spreadsheet_id = (parameters.get("spreadsheetId") or "").strip()
        if not spreadsheet_id:
            return ToolResult(success=False, output="", error="Spreadsheet ID is required.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        
        url = f"https://www.googleapis.com/drive/v3/files/{spreadsheet_id}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)
                
                if response.is_success:
                    data = {
                        "spreadsheetId": spreadsheet_id,
                        "deleted": True,
                    }
                    output = json.dumps(data)
                    return ToolResult(success=True, output=output, data=data)
                else:
                    error_msg = response.text
                    try:
                        error_data = response.json()
                        if isinstance(error_data, dict):
                            error = error_data.get("error")
                            if isinstance(error, dict):
                                error_msg = error.get("message", error_msg)
                    except:
                        pass
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")