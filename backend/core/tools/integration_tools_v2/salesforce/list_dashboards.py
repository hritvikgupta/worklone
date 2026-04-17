from typing import Any, Dict
import httpx
import base64
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class SalesforceListDashboardsTool(BaseTool):
    name = "salesforce_list_dashboards"
    description = "Get a list of dashboards accessible by the current user"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="SALESFORCE_ACCESS_TOKEN",
                description="Salesforce access token",
                env_var="SALESFORCE_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "salesforce",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("SALESFORCE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def _get_instance_url(self, id_token: str | None, instance_url: str | None) -> str:
        if instance_url and not self._is_placeholder_token(instance_url):
            return instance_url.rstrip("/")
        if not id_token or self._is_placeholder_token(id_token):
            raise ValueError("No valid instance URL or ID token provided")
        try:
            parts = id_token.split(".")
            if len(parts) != 3:
                raise ValueError("Invalid JWT format in ID token")
            payload = parts[1]
            padding = "=" * (4 - len(payload) % 4)
            decoded = base64.urlsafe_b64decode(payload + padding)
            payload_dict = json.loads(decoded)
            iss = payload_dict.get("iss")
            if not iss:
                raise ValueError("No 'iss' claim found in ID token")
            return iss.rstrip("/")
        except Exception as e:
            raise ValueError(f"Failed to parse instance URL from ID token: {str(e)}")

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "folderName": {
                    "type": "string",
                    "description": "Filter dashboards by folder name (case-insensitive partial match)",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        id_token = context.get("idToken") if context else None
        instance_url_param = context.get("instanceUrl") if context else None
        
        try:
            instance_url = self._get_instance_url(id_token, instance_url_param)
        except ValueError as e:
            return ToolResult(success=False, output="", error=str(e))
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = f"{instance_url}/services/data/v59.0/analytics/dashboards"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    dashboards = data.get("dashboards") or data or []
                    folder_name = parameters.get("folderName")
                    if folder_name:
                        lower_folder_name = folder_name.lower()
                        dashboards = [
                            d for d in dashboards
                            if lower_folder_name in d.get("folderName", "").lower()
                        ]
                    output_data = {
                        "dashboards": dashboards,
                        "totalReturned": len(dashboards),
                        "success": True,
                    }
                    return ToolResult(
                        success=True,
                        output=json.dumps(output_data),
                        data=output_data,
                    )
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")