from typing import Any, Dict, List
import httpx
import json
import base64
from urllib.parse import quote, urlencode
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleSheetsUpdateTool(BaseTool):
    name = "google_sheets_update"
    description = "Update data in a specific sheet in a Google Sheets spreadsheet"
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
            context_token_keys=("provider_token",),
            env_token_keys=("GOOGLE_SHEETS_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def _process_values(self, values: Any) -> List[List[Any]]:
        processed_values = values or []
        if not isinstance(processed_values, list):
            processed_values = [[processed_values]]
        else:
            processed_values = [
                item if isinstance(item, list) else [item]
                for item in processed_values
            ]
        if len(processed_values) > 0 and isinstance(processed_values[0], dict):
            all_keys: set[str] = set()
            for obj in processed_values:
                if isinstance(obj, dict):
                    all_keys.update(obj.keys())
            headers = list(all_keys)
            rows: List[List[Any]] = []
            for obj in processed_values:
                if not isinstance(obj, dict):
                    row = [""] * len(headers)
                else:
                    row = []
                    for key in headers:
                        if key not in obj:
                            row_val = ""
                        elif obj[key] is None:
                            row_val = None
                        elif isinstance(obj[key], (dict, list)):
                            row_val = json.dumps(obj[key])
                        else:
                            row_val = obj[key]
                        row.append(row_val)
                rows.append(row)
            processed_values = [headers] + rows
        return processed_values

    def _build_url(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        cell_range: str,
        value_input_option: str,
        include_values_in_response: bool,
    ) -> str:
        full_range = f"{sheet_name}!{cell_range}"
        base_url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{quote(full_range)}"
        params: Dict[str, str] = {
            "valueInputOption": value_input_option,
        }
        if include_values_in_response:
            params["includeValuesInResponse"] = "true"
        query = urlencode(params)
        return f"{base_url}?{query}" if query else base_url

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
                    "description": "The name of the sheet/tab to update",
                },
                "cellRange": {
                    "type": "string",
                    "description": r'The cell range to update (e.g. "A1:D10", "A1"). Defaults to "A1" if not specified.',
                },
                "values": {
                    "type": "array",
                    "description": "The data to update as a 2D array (e.g. [['Name', 'Age'], ['Alice', 30]]) or array of objects.",
                    "items": {
                        "anyOf": [
                            {"type": "array"},
                            {"type": "object", "additionalProperties": True},
                        ]
                    },
                },
            },
            "required": ["spreadsheetId", "sheetName", "values"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        spreadsheet_id = parameters["spreadsheetId"]
        sheet_name = parameters["sheetName"].strip()
        cell_range = (parameters.get("cellRange") or "").strip() or "A1"
        values = parameters["values"]
        value_input_option = parameters.get("valueInputOption", "USER_ENTERED")
        include_values_in_response = parameters.get("includeValuesInResponse", False)
        
        url = self._build_url(
            spreadsheet_id,
            sheet_name,
            cell_range,
            value_input_option,
            include_values_in_response,
        )
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        body = {
            "majorDimension": "ROWS",
            "values": self._process_values(values),
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.put(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")