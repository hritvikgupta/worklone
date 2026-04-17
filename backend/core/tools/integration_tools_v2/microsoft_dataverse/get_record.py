from typing import Any, Dict
import httpx
import os
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class MicrosoftDataverseGetRecordTool(BaseTool):
    name = "microsoft_dataverse_get_record"
    description = "Retrieve a single record from a Microsoft Dataverse table by its ID. Supports $select and $expand OData query options."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="accessToken",
                description="OAuth access token for Microsoft Dataverse API",
                env_var="MICROSOFT_DATAVERSE_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            ),
            CredentialRequirement(
                key="environmentUrl",
                description="Dataverse environment URL (e.g., https://myorg.crm.dynamics.com)",
                env_var="DATAVERSE_ENVIRONMENT_URL",
                required=True,
                auth_type="custom",
            ),
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

    def _resolve_environment_url(self, context: dict | None) -> str:
        value = context.get("environmentUrl") if context else None
        if value is None:
            value = os.getenv("DATAVERSE_ENVIRONMENT_URL")
        if self._is_placeholder_token(value or ""):
            raise ValueError("Dataverse environment URL not configured.")
        return (value or "").strip().rstrip("/")

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "entitySetName": {
                    "type": "string",
                    "description": "Entity set name (plural table name, e.g., accounts, contacts)",
                },
                "recordId": {
                    "type": "string",
                    "description": "The unique identifier (GUID) of the record to retrieve",
                },
                "select": {
                    "type": "string",
                    "description": "Comma-separated list of columns to return (OData $select)",
                },
                "expand": {
                    "type": "string",
                    "description": "Navigation properties to expand (OData $expand)",
                },
            },
            "required": ["entitySetName", "recordId"],
            "additionalProperties": False,
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        environment_url = self._resolve_environment_url(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
            "Accept": "application/json",
            "Prefer": 'odata.include-annotations="*"',
        }

        entity_set_name = parameters["entitySetName"]
        record_id = parameters["recordId"]
        select = parameters.get("select")
        expand = parameters.get("expand")

        query_parts: list[str] = []
        if select:
            query_parts.append(f"$select={select}")
        if expand:
            query_parts.append(f"$expand={expand}")
        query = "?" + "&".join(query_parts) if query_parts else ""
        url = f"{environment_url}/api/data/v9.2/{entity_set_name}({record_id}){query}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code != 200:
                    try:
                        error_data = response.json()
                        error_message = error_data.get("error", {}).get("message", f"Dataverse API error: {response.status_code} {response.reason_phrase}")
                    except Exception:
                        error_message = f"Dataverse API error: {response.status_code} {response.reason_phrase}"
                    return ToolResult(success=False, output="", error=error_message)

                data = response.json()
                id_key = next((k for k in data if k.endswith("id") and not k.startswith("@")), None)
                record_id_resp = str(data.get(id_key, "")) if id_key else ""
                transformed_data = {
                    "record": data,
                    "recordId": record_id_resp,
                    "success": True,
                }
                return ToolResult(success=True, output=response.text, data=transformed_data)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")