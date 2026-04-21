from typing import Any, Dict, List
import httpx
import json
import urllib.parse
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class GoogleSheetsWriteTool(BaseTool):
    name = "google_sheets_write"
    description = "Write data to a specific sheet in a Google Sheets spreadsheet"
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
                    "description": "The name of the sheet/tab to write to",
                },
                "cellRange": {
                    "type": "string",
                    "description": 'The cell range to write to (e.g. "A1:D10", "A1"). Defaults to "A1" if not specified.',
                },
                "values": {
                    "type": "array",
                    "description": 'The data to write as a 2D array (e.g. [["Name", "Age"], ["Alice", 30], ["Bob", 25]]) or array of objects.',
                },
            },
            "required": ["spreadsheetId", "sheetName", "values"],
        }

    def _process_values(self, values: List[Any], major_dimension: str) -> Dict[str, Any]:
        processed_values: List[List[Any]] = values[:] if values else []
        if processed_values and isinstance(processed_values[0], dict):
            all_keys: set[str] = set()
            for obj in processed_values:
                if isinstance(obj, dict):
                    all_keys.update(obj.keys())
            headers: List[str] = list(all_keys)
            rows: List[List[Any]] = []
            for obj in processed_values:
                if not isinstance(obj, dict):
                    rows.append([""] * len(headers))
                    continue
                row: List[Any] = []
                for key in headers:
                    value = obj.get(key)
                    if value is None:
                        row.append("")
                    elif isinstance(value, (dict, list)):
                        row.append(json.dumps(value))
                    else:
                        row.append(value)
                rows.append(row)
            processed_values = [headers] + rows
        return {
            "majorDimension": major_dimension,
            "values": processed_values,
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        try:
            spreadsheet_id = parameters["spreadsheetId"].strip()
            sheet_name = parameters["sheetName"].strip()
            if not sheet_name:
                return ToolResult(success=False, output="", error="Sheet name is required")
            cell_range = (parameters.get("cellRange") or "").strip() or "A1"
            full_range = f"{sheet_name}!{cell_range}"
            value_input_option = parameters.get("valueInputOption", "USER_ENTERED")
            include_values_in_response = parameters.get("includeValuesInResponse", False)
            major_dimension = parameters.get("majorDimension", "ROWS")

            path_range = urllib.parse.quote(full_range)
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{path_range}"
            
            query_params = {
                "valueInputOption": value_input_option,
            }
            if include_values_in_response:
                query_params["includeValuesInResponse"] = "true"
            
            body = self._process_values(parameters["values"], major_dimension)
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.put(url, headers=headers, params=query_params, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")