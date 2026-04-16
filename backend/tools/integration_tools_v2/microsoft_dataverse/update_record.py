from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class MicrosoftDataverseUpdateRecordTool(BaseTool):
    name = "microsoft_dataverse_update_record"
    description = "Update an existing record in a Microsoft Dataverse table. Only send the columns you want to change."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="DATAVERSE_ACCESS_TOKEN",
                description="OAuth access token for Microsoft Dataverse API",
                env_var="DATAVERSE_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "microsoft-dataverse",
            context=context,
            context_token_keys=("access_token",),
            env_token_keys=("DATAVERSE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "environmentUrl": {
                    "type": "string",
                    "description": "Dataverse environment URL (e.g., https://myorg.crm.dynamics.com)",
                },
                "entitySetName": {
                    "type": "string",
                    "description": "Entity set name (plural table name, e.g., accounts, contacts)",
                },
                "recordId": {
                    "type": "string",
                    "description": "The unique identifier (GUID) of the record to update",
                },
                "data": {
                    "type": "object",
                    "description": "Record data to update as a JSON object with column names as keys",
                },
            },
            "required": ["environmentUrl", "entitySetName", "recordId", "data"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
            "Accept": "application/json",
            "If-Match": "*",
        }
        
        environment_url = parameters["environmentUrl"].rstrip("/")
        entity_set_name = parameters["entitySetName"]
        record_id = parameters["recordId"]
        data = parameters["data"]
        url = f"{environment_url}/api/data/v9.2/{entity_set_name}({record_id})"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(url, headers=headers, json=data)
                
                if response.status_code in [200, 204]:
                    return ToolResult(
                        success=True,
                        output="",
                        data={"recordId": record_id, "success": True},
                    )
                else:
                    error_msg = response.text
                    try:
                        error_json = response.json()
                        error_msg = error_json.get("error", {}).get("message", error_msg)
                    except Exception:
                        pass
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")