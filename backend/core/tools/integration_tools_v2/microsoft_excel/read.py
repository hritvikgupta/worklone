from typing import Any, Dict, List
import httpx
from urllib.parse import quote
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class MicrosoftExcelReadTool(BaseTool):
    name = "microsoft_excel_read"
    description = "Read data from a specific sheet in a Microsoft Excel spreadsheet"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="MICROSOFT_EXCEL_ACCESS_TOKEN",
                description="Access token for the Microsoft Excel API",
                env_var="MICROSOFT_EXCEL_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "microsoft-excel",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("MICROSOFT_EXCEL_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def _trim_trailing_empty_rows_and_columns(self, values: list[list[Any]]) -> list[list[Any]]:
        if not values:
            return []
        # Trim trailing empty rows
        while values and all(cell is None or cell == "" for cell in values[-1]):
            values.pop()
        if not values:
            return []
        # Trim trailing empty columns (assumes rectangular array)
        num_rows = len(values)
        num_cols = len(values[0])
        for col in range(num_cols - 1, -1, -1):
            if all(values[row][col] is None or values[row][col] == "" for row in range(num_rows)):
                for row in range(num_rows):
                    values[row].pop()
            else:
                break
        return values

    async def _get_spreadsheet_web_url(self, spreadsheet_id: str, access_token: str) -> str:
        url = f"https://graph.microsoft.com/v1.0/me/drive/items/{spreadsheet_id}"
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    return data.get("webUrl", "")
                return ""
        except Exception:
            return ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "spreadsheetId": {
                    "type": "string",
                    "description": "The ID of the spreadsheet/workbook to read from (e.g., \"01ABC123DEF456\")",
                },
                "sheetName": {
                    "type": "string",
                    "description": "The name of the sheet/tab to read from (e.g., \"Sheet1\", \"Sales Data\")",
                },
                "cellRange": {
                    "type": "string",
                    "description": "The cell range to read (e.g., \"A1:D10\"). If not specified, reads the entire used range.",
                },
            },
            "required": ["spreadsheetId", "sheetName"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        
        spreadsheet_id = (parameters.get("spreadsheetId") or "").strip()
        if not spreadsheet_id:
            return ToolResult(success=False, output="", error="Spreadsheet ID is required")
        
        sheet_name = (parameters.get("sheetName") or "").strip()
        if not sheet_name:
            return ToolResult(success=False, output="", error="Sheet name is required")
        
        cell_range = (parameters.get("cellRange") or "").strip()
        sheet_name_encoded = quote(sheet_name)
        
        if cell_range:
            address_encoded = quote(cell_range)
            url = f"https://graph.microsoft.com/v1.0/me/drive/items/{spreadsheet_id}/workbook/worksheets('{sheet_name_encoded}')/range(address='{address_encoded}')"
        else:
            url = f"https://graph.microsoft.com/v1.0/me/drive/items/{spreadsheet_id}/workbook/worksheets('{sheet_name_encoded}')/usedRange(valuesOnly=true)"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code != 200:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                address = data.get("address") or data.get("addressLocal") or ""
                raw_values: list[list[Any]] = data.get("values", [])
                values = self._trim_trailing_empty_rows_and_columns(raw_values)
                
                final_sheet_name = sheet_name
                if "!" in address and not final_sheet_name:
                    final_sheet_name = address.split("!")[0]
                
                web_url = await self._get_spreadsheet_web_url(spreadsheet_id, access_token)
                
                output_data = {
                    "sheetName": final_sheet_name,
                    "range": address,
                    "values": values,
                    "metadata": {
                        "spreadsheetId": spreadsheet_id,
                        "spreadsheetUrl": web_url,
                    },
                }
                
                return ToolResult(success=True, output=str(output_data), data=output_data)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")