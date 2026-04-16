from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleSheetsCopySheetTool(BaseTool):
    name = "google_sheets_copy_sheet_v2"
    description = "Copy a sheet from one spreadsheet to another"
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
                "sourceSpreadsheetId": {
                    "type": "string",
                    "description": "Source Google Sheets spreadsheet ID",
                },
                "sheetId": {
                    "type": "number",
                    "description": "The ID of the sheet to copy (numeric ID, not the sheet name). Use Get Spreadsheet to find sheet IDs.",
                },
                "destinationSpreadsheetId": {
                    "type": "string",
                    "description": "The ID of the destination spreadsheet where the sheet will be copied",
                },
            },
            "required": ["sourceSpreadsheetId", "sheetId", "destinationSpreadsheetId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        source_spreadsheet_id = (parameters.get("sourceSpreadsheetId") or "").strip()
        if not source_spreadsheet_id:
            return ToolResult(success=False, output="", error="Source spreadsheet ID is required")
        
        sheet_id = parameters.get("sheetId")
        if sheet_id is None:
            return ToolResult(success=False, output="", error="Sheet ID is required")
        
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{source_spreadsheet_id}/sheets/{sheet_id}:copyTo"
        
        destination_spreadsheet_id = (parameters.get("destinationSpreadsheetId") or "").strip()
        if not destination_spreadsheet_id:
            return ToolResult(success=False, output="", error="Destination spreadsheet ID is required")
        
        json_body = {
            "destinationSpreadsheetId": destination_spreadsheet_id,
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=json_body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")