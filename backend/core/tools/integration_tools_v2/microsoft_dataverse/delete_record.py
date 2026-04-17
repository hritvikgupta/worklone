from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class MicrosoftDataverseDeleteRecordTool(BaseTool):
    name = "microsoft_dataverse_delete_record"
    description = "Delete a record from a Microsoft Dataverse table by its ID."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="MICROSOFT_DATAVERSE_ACCESS_TOKEN",
                description="OAuth access token for Microsoft Dataverse API",
                env_var="MICROSOFT_DATAVERSE_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "microsoft-dataverse",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("MICROSOFT_DATAVERSE_ACCESS_TOKEN",),
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
                    "description": "The unique identifier (GUID) of the record to delete",
                },
            },
            "required": ["environmentUrl", "entitySetName", "recordId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        environment_url = parameters["environmentUrl"]
        entity_set_name = parameters["entitySetName"]
        record_id = parameters["recordId"]
        
        url = f"{environment_url.rstrip('/')}/api/data/v9.2/{entity_set_name}({record_id})"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
            "Accept": "application/json",
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(
                        success=True,
                        output="",
                        data={
                            "recordId": record_id,
                            "success": True,
                        },
                    )
                else:
                    error_data = {}
                    try:
                        error_data = response.json()
                    except:
                        pass
                    error_message = (
                        error_data.get("error", {}).get("message", response.text)
                        or f"Dataverse API error: {response.status_code} {response.reason_phrase}"
                    ).strip()
                    return ToolResult(success=False, output="", error=error_message)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")