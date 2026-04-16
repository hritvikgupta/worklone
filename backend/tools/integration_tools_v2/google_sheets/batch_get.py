from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleSheetsBatchGetTool(BaseTool):
    name = "google_sheets_batch_get"
    description = "Read multiple ranges from a Google Sheets spreadsheet in a single request"
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
            context_token_keys=("google_sheets_token",),
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
                "ranges": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": 'Array of ranges to read (e.g., ["Sheet1!A1:D10", "Sheet2!A1:B5"]). Each range should include sheet name.',
                },
                "majorDimension": {
                    "type": "string",
                    "description": 'The major dimension of values: "ROWS" (default) or "COLUMNS"',
                },
                "valueRenderOption": {
                    "type": "string",
                    "description": 'How values should be rendered: "FORMATTED_VALUE" (default), "UNFORMATTED_VALUE", or "FORMULA"',
                },
            },
            "required": ["spreadsheetId", "ranges"],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        
        spreadsheet_id = parameters.get("spreadsheetId", "").strip()
        if not spreadsheet_id:
            return ToolResult(success=False, output="", error="Spreadsheet ID is required")
        
        ranges = parameters.get("ranges")
        if not ranges or not isinstance(ranges, list) or len(ranges) == 0:
            return ToolResult(success=False, output="", error="At least one range is required")
        
        query_params: Dict[str, Any] = {
            "ranges": [str(r) for r in ranges],
        }
        major_dimension = parameters.get("majorDimension")
        if major_dimension:
            query_params["majorDimension"] = major_dimension
        value_render_option = parameters.get("valueRenderOption")
        if value_render_option:
            query_params["valueRenderOption"] = value_render_option
        
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values:batchGet"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)
                
                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    value_ranges = []
                    if data.get("valueRanges"):
                        for vr in data["valueRanges"]:
                            value_ranges.append({
                                "range": vr.get("range", ""),
                                "majorDimension": vr.get("majorDimension", "ROWS"),
                                "values": vr.get("values", []),
                            })
                    spreadsheet_id_resp = data.get("spreadsheetId", "")
                    output_data = {
                        "spreadsheetId": spreadsheet_id_resp,
                        "valueRanges": value_ranges,
                        "metadata": {
                            "spreadsheetId": spreadsheet_id_resp,
                            "spreadsheetUrl": f"https://docs.google.com/spreadsheets/d/{spreadsheet_id_resp}" if spreadsheet_id_resp else "",
                        },
                    }
                    return ToolResult(success=True, output=response.text, data=output_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")