from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class MicrosoftExcelWorksheetAddTool(BaseTool):
    name = "microsoft_excel_worksheet_add"
    description = "Create a new worksheet (sheet) in a Microsoft Excel workbook"
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

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "spreadsheetId": {
                    "type": "string",
                    "description": "The ID of the Excel workbook to add the worksheet to (e.g., \"01ABC123DEF456\")",
                },
                "worksheetName": {
                    "type": "string",
                    "description": "The name of the new worksheet (e.g., \"Sales Q1\", \"Data\"). Must be unique within the workbook and cannot exceed 31 characters",
                },
            },
            "required": ["spreadsheetId", "worksheetName"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
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
        
        worksheet_name = (parameters.get("worksheetName") or "").strip()
        if not worksheet_name:
            return ToolResult(success=False, output="", error="Worksheet name is required")
        
        if len(worksheet_name) > 31:
            return ToolResult(success=False, output="", error="Worksheet name cannot exceed 31 characters. Please provide a shorter name")
        
        invalid_chars = ["\\", "/", "?", "*", "[", "]", ":"]
        for char in invalid_chars:
            if char in worksheet_name:
                return ToolResult(success=False, output="", error="Worksheet name cannot contain the following characters: \\ / ? * [ ] :")
        
        url = f"https://graph.microsoft.com/v1.0/me/drive/items/{spreadsheet_id}/workbook/worksheets/add"
        json_body = {
            "name": worksheet_name,
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=json_body)
                
                if response.status_code in [200, 201]:
                    data = response.json()
                    worksheet = {
                        "id": data.get("id", ""),
                        "name": data.get("name", ""),
                        "position": data.get("position", 0),
                        "visibility": data.get("visibility", "Visible"),
                    }
                    
                    web_response = await client.get(
                        f"https://graph.microsoft.com/v1.0/me/drive/items/{spreadsheet_id}?select=webUrl",
                        headers=headers,
                    )
                    web_url = ""
                    if web_response.status_code == 200:
                        web_data = web_response.json()
                        web_url = web_data.get("webUrl", "")
                    
                    result_data = {
                        "worksheet": worksheet,
                        "metadata": {
                            "spreadsheetId": spreadsheet_id,
                            "spreadsheetUrl": web_url,
                        },
                    }
                    return ToolResult(success=True, output=json.dumps(result_data), data=result_data)
                elif response.status_code == 409:
                    return ToolResult(success=False, output="", error="A worksheet with this name already exists. Please choose a different name")
                else:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("error", {}).get("message", response.text)
                    except Exception:
                        error_msg = response.text or f"HTTP {response.status_code}: {response.reason_phrase}"
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")