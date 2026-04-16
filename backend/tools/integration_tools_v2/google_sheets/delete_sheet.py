from typing import Any, Dict
import httpx
import json
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleSheetsDeleteSheetTool(BaseTool):
    name = "google_sheets_delete_sheet"
    description = "Delete a sheet/tab from a Google Sheets spreadsheet"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GOOGLE_SHEETS_ACCESS_TOKEN",
                description="The access token for the Google Sheets API",
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
                    "description": "Google Sheets spreadsheet ID",
                },
                "sheetId": {
                    "type": "number",
                    "description": "The numeric ID of the sheet/tab to delete (not the sheet name). Use Get Spreadsheet to find sheet IDs.",
                },
            },
            "required": ["spreadsheetId", "sheetId"],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        spreadsheet_id = (parameters.get("spreadsheetId") or "").strip()
        if not spreadsheet_id:
            return ToolResult(success=False, output="", error="Spreadsheet ID is required")
        
        sheet_id = parameters.get("sheetId")
        if sheet_id is None:
            return ToolResult(success=False, output="", error="Sheet ID is required")
        
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate"
        
        body = {
            "requests": [
                {
                    "deleteSheet": {
                        "sheetId": int(sheet_id),
                    },
                },
            ],
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    output_data = {
                        "spreadsheetId": spreadsheet_id,
                        "deletedSheetId": int(sheet_id),
                        "metadata": {
                            "spreadsheetId": spreadsheet_id,
                            "spreadsheetUrl": f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}",
                        },
                    }
                    return ToolResult(
                        success=True,
                        output=json.dumps(output_data),
                        data=output_data,
                    )
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")