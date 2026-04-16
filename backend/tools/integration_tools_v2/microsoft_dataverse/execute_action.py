from typing import Any, Dict
import httpx
import json
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class MicrosoftDataverseExecuteActionTool(BaseTool):
    name = "microsoft_dataverse_execute_action"
    description = "Execute a bound or unbound Dataverse action. Actions perform operations with side effects (e.g., Merge, GrantAccess, SendEmail, QualifyLead). For bound actions, provide the entity set name and record ID."
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
            context_token_keys=("provider_token",),
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
                "actionName": {
                    "type": "string",
                    "description": "Action name (e.g., Merge, GrantAccess, SendEmail). Do not include the Microsoft.Dynamics.CRM. namespace prefix for unbound actions.",
                },
                "entitySetName": {
                    "type": "string",
                    "description": "Entity set name for bound actions (e.g., accounts). Leave empty for unbound actions.",
                },
                "recordId": {
                    "type": "string",
                    "description": "Record GUID for bound actions. Leave empty for unbound or collection-bound actions.",
                },
                "parameters": {
                    "type": "object",
                    "description": "Action parameters as a JSON object. For entity references, include @odata.type annotation (e.g., {\"Target\": {\"@odata.type\": \"Microsoft.Dynamics.CRM.account\", \"accountid\": \"...\"}})",
                },
            },
            "required": ["environmentUrl", "actionName"],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
            "Accept": "application/json",
        }

        environment_url = parameters["environmentUrl"]
        action_name = parameters["actionName"]
        entity_set_name = parameters.get("entitySetName")
        record_id = parameters.get("recordId")

        base_url = environment_url.rstrip("/")
        if entity_set_name:
            if record_id:
                url = f"{base_url}/api/data/v9.2/{entity_set_name}({record_id})/Microsoft.Dynamics.CRM.{action_name}"
            else:
                url = f"{base_url}/api/data/v9.2/{entity_set_name}/Microsoft.Dynamics.CRM.{action_name}"
        else:
            url = f"{base_url}/api/data/v9.2/{action_name}"

        body_raw = parameters.get("parameters")
        if body_raw is None:
            body = {}
        elif isinstance(body_raw, str):
            try:
                body = json.loads(body_raw)
            except json.JSONDecodeError:
                return ToolResult(success=False, output="", error="Invalid JSON format for action parameters")
        else:
            body = body_raw

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    data = None
                    if response.status_code != 204 and response.content:
                        try:
                            data = response.json()
                        except:
                            data = None
                    return ToolResult(success=True, output=response.text, data=data)
                else:
                    error_data = {}
                    try:
                        error_data = response.json()
                    except:
                        pass
                    error_message = (
                        error_data.get("error", {}).get("message")
                        or f"Dataverse API error: {response.status_code} {response.reason_phrase}"
                    )
                    return ToolResult(success=False, output="", error=error_message)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")