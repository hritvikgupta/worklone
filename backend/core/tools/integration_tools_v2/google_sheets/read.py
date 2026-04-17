from typing import Any, Dict
import httpx
import json
import urllib.parse
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleSheetsReadTool(BaseTool):
    name = "google_sheets_read"
    description = "Read data from a specific sheet in a Google Sheets spreadsheet"
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
            "google",
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
                "sheetName": {
                    "type": "string",
                    "description": "The name of the sheet/tab to read from",
                },
                "cellRange": {
                    "type": "string",
                    "description": 'The cell range to read (e.g. "A1:D10"). Defaults to "A1:Z1000" if not specified.',
                },
                "filterColumn": {
                    "type": "string",
                    "description": "Column name (from header row) to filter on. If not provided, no filtering is applied.",
                },
                "filterValue": {
                    "type": "string",
                    "description": "Value to match against the filter column.",
                },
                "filterMatchType": {
                    "type": "string",
                    "description": 'How to match the filter value: "contains", "exact", "starts_with", or "ends_with". Defaults to "contains".',
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
        sheet_name = (parameters.get("sheetName") or "").strip()
        if not spreadsheet_id or not sheet_name:
            return ToolResult(success=False, output="", error="Spreadsheet ID and sheet name are required.")
        
        cell_range = (parameters.get("cellRange") or "").strip()
        if not cell_range:
            cell_range = "A1:Z1000"
        full_range = f"{sheet_name}!{cell_range}"
        full_range_encoded = urllib.parse.quote(full_range)
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{full_range_encoded}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    
                    resp_url = str(response.url)
                    spreadsheet_id_resp = ""
                    if "/spreadsheets/" in resp_url:
                        url_parts = resp_url.split("/spreadsheets/")
                        if len(url_parts) > 1:
                            spreadsheet_id_resp = url_parts[1].split("/")[0]
                    
                    metadata = {
                        "spreadsheetId": spreadsheet_id_resp,
                        "spreadsheetUrl": f"https://docs.google.com/spreadsheets/d/{spreadsheet_id_resp}",
                    }
                    
                    values: list[list[Any]] = data.get("values", [])
                    
                    filter_column = parameters.get("filterColumn")
                    filter_value = parameters.get("filterValue")
                    if filter_column and filter_value is not None and len(values) > 1:
                        headers_row = values[0]
                        column_index = -1
                        for i, h in enumerate(headers_row):
                            if str(h).lower() == str(filter_column).lower():
                                column_index = i
                                break
                        
                        if column_index != -1:
                            match_type = parameters.get("filterMatchType", "contains")
                            filter_val = str(filter_value).lower()
                            filtered_rows: list[list[Any]] = []
                            for row in values[1:]:
                                cell_value_str = ""
                                if column_index < len(row):
                                    cell_value_str = str(row[column_index] or "")
                                cell_value = cell_value_str.lower()
                                
                                match = False
                                if match_type == "exact":
                                    match = cell_value == filter_val
                                elif match_type == "starts_with":
                                    match = cell_value.startswith(filter_val)
                                elif match_type == "ends_with":
                                    match = cell_value.endswith(filter_val)
                                else:
                                    match = filter_val in cell_value
                                
                                if match:
                                    filtered_rows.append(row)
                            
                            values = [values[0]] + filtered_rows
                    
                    output_data = {
                        "sheetName": sheet_name,
                        "range": data.get("range", ""),
                        "values": values,
                        "metadata": metadata,
                    }
                    
                    return ToolResult(success=True, output=json.dumps(output_data), data=output_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")