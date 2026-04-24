from typing import Any, Dict, List
import httpx
import json
import urllib.parse
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class MicrosoftExcelWriteTool(BaseTool):
    name = "microsoft_excel_write"
    description = "Write data to a specific sheet in a Microsoft Excel spreadsheet"
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
        connection = await resolve_oauth_connection("microsoft_excel",
            context=context,
            context_token_keys=("provider_token",),
            env_token_keys=("MICROSOFT_EXCEL_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def _process_values(self, values: list[Any]) -> list[list[Any]]:
        if not isinstance(values, list) or len(values) == 0:
            return []
        first_item = values[0]
        if not isinstance(first_item, dict):
            return values
        all_keys: set[str] = set()
        for obj in values:
            if isinstance(obj, dict):
                all_keys.update(obj.keys())
        headers = list(all_keys)
        rows: list[list[Any]] = []
        for obj in values:
            if not isinstance(obj, dict):
                rows.append([""] * len(headers))
                continue
            row: list[Any] = []
            for key in headers:
                value = obj.get(key)
                if value is not None and isinstance(value, (dict, list)):
                    row.append(json.dumps(value))
                else:
                    row.append("" if value is None else value)
            rows.append(row)
        return [headers] + rows

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "spreadsheetId": {
                    "type": "string",
                    "description": "The ID of the spreadsheet/workbook to write to (e.g., \"01ABC123DEF456\")",
                },
                "sheetName": {
                    "type": "string",
                    "description": "The name of the sheet/tab to write to (e.g., \"Sheet1\", \"Sales Data\")",
                },
                "cellRange": {
                    "type": "string",
                    "description": "The cell range to write to (e.g., \"A1:D10\", \"A1\"). Defaults to \"A1\" if not specified.",
                },
                "values": {
                    "type": "array",
                    "description": "The data to write as a 2D array (e.g. [[\"Name\", \"Age\"], [\"Alice\", 30], [\"Bob\", 25]]) or array of objects.",
                },
                "valueInputOption": {
                    "type": "string",
                    "description": "The format of the data to write",
                },
                "includeValuesInResponse": {
                    "type": "boolean",
                    "description": "Whether to include the written values in the response",
                },
            },
            "required": ["spreadsheetId", "sheetName", "values"],
        }

    async def execute(self, parameters: Dict[str, Any], context: dict = None) -> ToolResult:
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
        
        sheet_name = (parameters.get("sheetName") or "").strip()
        if not sheet_name:
            return ToolResult(success=False, output="", error="Sheet name is required")
        
        cell_range = (parameters.get("cellRange") or "").strip()
        if not cell_range:
            cell_range = "A1"
        
        encoded_sheet_name = urllib.parse.quote(sheet_name)
        encoded_cell_range = urllib.parse.quote(cell_range)
        
        base_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{spreadsheet_id}/workbook/worksheets('{encoded_sheet_name}')/range(address='{encoded_cell_range}')"
        parsed_url = urlparse(base_url)
        query_params = parse_qs(parsed_url.query) if parsed_url.query else {}
        query_params["valueInputOption"] = [parameters.get("valueInputOption", "USER_ENTERED")]
        if parameters.get("includeValuesInResponse"):
            query_params["includeValuesInResponse"] = ["true"]
        new_query = urlencode(query_params, doseq=True)
        url = urlunparse(parsed_url._replace(query=new_query))
        
        values = parameters.get("values", [])
        processed_values = self._process_values(values)
        major_dimension = parameters.get("majorDimension", "ROWS")
        body = {
            "majorDimension": major_dimension,
            "values": processed_values,
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(url, headers=headers, json=body)
                
                if response.status_code in [200, 201]:
                    try:
                        data = response.json()
                    except json.JSONDecodeError:
                        data = {}
                    
                    # Fetch web URL
                    item_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{spreadsheet_id}"
                    item_response = await client.get(item_url, headers=headers)
                    web_url = ""
                    if item_response.status_code == 200:
                        try:
                            item_data = item_response.json()
                            web_url = item_data.get("webUrl", "")
                        except json.JSONDecodeError:
                            pass
                    
                    output_data = {
                        "updatedRange": data.get("address"),
                        "updatedRows": data.get("rowCount") or 0,
                        "updatedColumns": data.get("columnCount") or 0,
                        "updatedCells": ((data.get("rowCount") or 0) * (data.get("columnCount") or 0)),
                        "metadata": {
                            "spreadsheetId": spreadsheet_id,
                            "spreadsheetUrl": web_url,
                        },
                    }
                    return ToolResult(success=True, output=json.dumps(output_data), data=output_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")