from typing import Any, Dict, List, Union
import httpx
import json
import urllib.parse
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class GoogleSheetsAppendTool(BaseTool):
    name = "google_sheets_append"
    description = "Append data to the end of a specific sheet in a Google Sheets spreadsheet"
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

    def _process_values(self, values: Any) -> List[List[Any]]:
        processed_values: Union[List, str, Any] = values or []
        if isinstance(processed_values, str):
            try:
                processed_values = json.loads(processed_values)
            except json.JSONDecodeError:
                try:
                    sanitized_input = processed_values.replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
                    processed_values = json.loads(sanitized_input)
                except json.JSONDecodeError:
                    processed_values = [[processed_values]]
        if (
            isinstance(processed_values, list)
            and len(processed_values) > 0
            and isinstance(processed_values[0], dict)
        ):
            all_keys: List[str] = []
            seen_keys: set[str] = set()
            for obj in processed_values:
                if isinstance(obj, dict):
                    for key in obj:
                        if key not in seen_keys:
                            seen_keys.add(key)
                            all_keys.append(key)
            headers = all_keys
            rows: List[List[Any]] = []
            for obj in processed_values:
                if not isinstance(obj, dict):
                    rows.append([""] * len(headers))
                    continue
                row: List[Any] = []
                for key in headers:
                    if key not in obj:
                        row.append("")
                    else:
                        value = obj[key]
                        if value is not None and isinstance(value, (dict, list)):
                            row.append(json.dumps(value))
                        else:
                            row.append(value)
                rows.append(row)
            processed_values = [headers] + rows
        elif not isinstance(processed_values, list):
            processed_values = [[str(processed_values)]]
        elif not all(isinstance(item, list) for item in processed_values):
            processed_values = [[str(item)] if not isinstance(item, list) else item for item in processed_values]
        return processed_values

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
                    "description": "The name of the sheet/tab to append to",
                },
                "values": {
                    "type": "array",
                    "description": "The data to append as a 2D array (e.g. [['Alice', 30], ['Bob', 25]]) or array of objects.",
                },
            },
            "required": ["spreadsheetId", "sheetName", "values"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        spreadsheet_id = parameters.get("spreadsheetId")
        if not spreadsheet_id:
            return ToolResult(success=False, output="", error="Spreadsheet ID is required.")
        
        sheet_name = (parameters.get("sheetName") or "").strip()
        if not sheet_name:
            return ToolResult(success=False, output="", error="Sheet name is required.")
        
        encoded_sheet_name = urllib.parse.quote(sheet_name)
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{encoded_sheet_name}:append"
        
        query_params = {
            "valueInputOption": parameters.get("valueInputOption", "USER_ENTERED"),
        }
        insert_data_option = parameters.get("insertDataOption")
        if insert_data_option:
            query_params["insertDataOption"] = insert_data_option
        include_values_in_response = parameters.get("includeValuesInResponse")
        if include_values_in_response:
            query_params["includeValuesInResponse"] = "true"
        
        processed_values = self._process_values(parameters.get("values"))
        body = {
            "majorDimension": parameters.get("majorDimension", "ROWS"),
            "values": processed_values,
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url, headers=headers, params=query_params, json=body
                )
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")