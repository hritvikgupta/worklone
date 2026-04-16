from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleSheetsCreateSpreadsheetTool(BaseTool):
    name = "google_sheets_create_spreadsheet"
    description = "Create a new Google Sheets spreadsheet"
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
                "title": {
                    "type": "string",
                    "description": "The title of the new spreadsheet",
                },
                "sheetTitles": {
                    "type": "array",
                    "items": {
                        "type": "string",
                    },
                    "description": 'Array of sheet names to create (e.g., ["Sheet1", "Data", "Summary"]). Defaults to a single "Sheet1".',
                },
                "locale": {
                    "type": "string",
                    "description": 'The locale of the spreadsheet (e.g., "en_US")',
                },
                "timeZone": {
                    "type": "string",
                    "description": 'The time zone of the spreadsheet (e.g., "America/New_York")',
                },
            },
            "required": ["title"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        title = (parameters.get("title") or "").strip()
        if not title:
            return ToolResult(success=False, output="", error="Spreadsheet title is required")
        
        sheet_titles = parameters.get("sheetTitles", ["Sheet1"])
        sheets = [
            {
                "properties": {
                    "title": sheet_title,
                    "index": index,
                }
            }
            for index, sheet_title in enumerate(sheet_titles)
        ]
        
        body = {
            "properties": {
                "title": title,
            },
            "sheets": sheets,
        }
        
        locale = parameters.get("locale")
        if locale:
            body["properties"]["locale"] = locale
        
        time_zone = parameters.get("timeZone")
        if time_zone:
            body["properties"]["timeZone"] = time_zone
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = "https://sheets.googleapis.com/v4/spreadsheets"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")