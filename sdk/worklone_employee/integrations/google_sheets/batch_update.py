from typing import Any, Dict
import httpx
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class GoogleSheetsBatchUpdateTool(BaseTool):
    name = "google_sheets_batch_update_v2"
    description = "Update multiple ranges in a Google Sheets spreadsheet in a single request"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GOOGLE_SHEETS_ACCESS_TOKEN",
                description="Access token for Google Sheets API",
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
                "data": {
                    "type": "array",
                    "description": 'Array of value ranges to update. Each item should have "range" (e.g., "Sheet1!A1:D10") and "values" (2D array).',
                    "items": {
                        "type": "object",
                        "properties": {
                            "range": {
                                "type": "string",
                                "description": "The range to update (e.g., \"Sheet1!A1:D10\")",
                            },
                            "values": {
                                "type": "array",
                                "description": "2D array of values to insert",
                                "items": {
                                    "type": "array",
                                    "items": {},
                                },
                            },
                        },
                        "required": ["range", "values"],
                    },
                },
                "valueInputOption": {
                    "type": "string",
                    "description": 'How input data should be interpreted: "RAW" or "USER_ENTERED" (default). USER_ENTERED parses formulas.',
                },
            },
            "required": ["spreadsheetId", "data"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        spreadsheet_id = (parameters.get("spreadsheetId") or "").strip()
        if not spreadsheet_id:
            return ToolResult(success=False, output="", error="Spreadsheet ID is required")
        
        data = parameters.get("data")
        if not data or not isinstance(data, list) or len(data) == 0:
            return ToolResult(success=False, output="", error="At least one data range is required")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values:batchUpdate"
        
        body = {
            "valueInputOption": parameters.get("valueInputOption", "USER_ENTERED"),
            "data": [
                {
                    "range": item.get("range"),
                    "values": item.get("values"),
                }
                for item in data
            ],
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")