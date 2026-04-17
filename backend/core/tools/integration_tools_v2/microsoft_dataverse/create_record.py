from typing import Any, Dict
import httpx
import json
import re
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class MicrosoftDataverseCreateRecordTool(BaseTool):
    name = "microsoft_dataverse_create_record"
    description = "Create a new record in a Microsoft Dataverse table. Requires the entity set name (plural table name) and record data as a JSON object."
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
                "data": {
                    "type": "object",
                    "description": "Record data as a JSON object with column names as keys",
                },
            },
            "required": ["environmentUrl", "entitySetName", "data"],
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
            "Prefer": "return=representation",
        }
        
        environment_url = parameters["environmentUrl"].rstrip("/")
        entity_set_name = parameters["entitySetName"]
        url = f"{environment_url}/api/data/v9.2/{entity_set_name}"
        
        request_data = parameters["data"]
        if isinstance(request_data, str):
            try:
                request_data = json.loads(request_data)
            except json.JSONDecodeError:
                return ToolResult(success=False, output="", error="Invalid JSON format for record data")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=request_data)
                
                if response.status_code in [200, 201, 204]:
                    try:
                        resp_data = response.json()
                    except:
                        resp_data = {}
                    
                    record_id = ""
                    id_key = next((k for k in resp_data if k.endswith("id") and not k.startswith("@")), None)
                    if id_key:
                        record_id = str(resp_data[id_key])
                    
                    if not record_id:
                        entity_id_header = response.headers.get("OData-EntityId")
                        if entity_id_header:
                            match = re.search(r"\(([^)]+)\)", entity_id_header)
                            if match:
                                record_id = match.group(1)
                    
                    output_data = {
                        "recordId": record_id,
                        "record": resp_data,
                        "success": True,
                    }
                    return ToolResult(success=True, output=json.dumps(output_data), data=output_data)
                else:
                    try:
                        error_data = response.json()
                        error_message = error_data.get("error", {}).get("message", f"Dataverse API error: {response.status_code} {response.status_code}")
                    except:
                        error_message = response.text
                    return ToolResult(success=False, output="", error=error_message)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")