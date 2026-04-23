from typing import Any, Dict, List
import httpx
import json
import urllib.parse
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class MicrosoftExcelTableAddTool(BaseTool):
    name = "microsoft_excel_table_add"
    description = "Add new rows to a Microsoft Excel table"
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

    def _process_values(self, values: Any) -> List[List[Any]]:
        if not isinstance(values, list) or len(values) == 0:
            raise ValueError("Values must be a non-empty array")
        processed_values = list(values)
        if len(processed_values) > 0 and isinstance(processed_values[0], dict):
            all_keys: set[str] = set()
            for obj in values:
                if isinstance(obj, dict):
                    all_keys.update(obj.keys())
            headers = list(all_keys)
            new_rows = []
            for obj in values:
                if not isinstance(obj, dict):
                    row = [""] * len(headers)
                else:
                    row = []
                    for key in headers:
                        value = obj.get(key)
                        if value is None:
                            row.append("")
                        elif isinstance(value, (dict, list)):
                            row.append(json.dumps(value))
                        else:
                            row.append(value)
                new_rows.append(row)
            processed_values = new_rows
        if len(processed_values) > 0 and not isinstance(processed_values[0], list):
            processed_values = [processed_values]
        return processed_values

    async def _get_spreadsheet_web_url(self, spreadsheet_id: str, access_token: str) -> str:
        url = f"https://graph.microsoft.com/v1.0/me/drive/items/{spreadsheet_id}?select=webUrl"
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    return response.json().get("webUrl", "")
                return ""
        except Exception:
            return ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "spreadsheetId": {
                    "type": "string",
                    "description": "The ID of the spreadsheet/workbook containing the table (e.g., \"01ABC123DEF456\")",
                },
                "tableName": {
                    "type": "string",
                    "description": "The name of the table to add rows to (e.g., \"Table1\", \"SalesTable\")",
                },
                "values": {
                    "type": "array",
                    "description": "The data to add as a 2D array (e.g., [[\"Alice\", 30], [\"Bob\", 25]]) or array of objects",
                },
            },
            "required": ["spreadsheetId", "tableName", "values"],
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
            processed_values = self._process_values(parameters["values"])
        except ValueError as e:
            return ToolResult(success=False, output="", error=str(e))
        
        table_name_encoded = urllib.parse.quote(parameters["tableName"])
        url = f"https://graph.microsoft.com/v1.0/me/drive/items/{parameters['spreadsheetId']}/workbook/tables('{table_name_encoded}')/rows/add"
        
        body = {
            "values": processed_values,
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    web_url = await self._get_spreadsheet_web_url(parameters["spreadsheetId"], access_token)
                    metadata = {
                        "spreadsheetId": parameters["spreadsheetId"],
                        "spreadsheetUrl": web_url,
                    }
                    output_data = {
                        "index": data.get("index", 0),
                        "values": data.get("values", []),
                        "metadata": metadata,
                    }
                    return ToolResult(success=True, output="Successfully added rows to the table.", data=output_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")