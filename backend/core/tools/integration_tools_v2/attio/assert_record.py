import json
from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class AttioAssertRecordTool(BaseTool):
    name = "attio_assert_record"
    description = "Upsert a record in Attio — creates it if no match is found, updates it if a match exists"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="ATTIO_ACCESS_TOKEN",
                description="Access token for the Attio API",
                env_var="ATTIO_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "attio",
            context=context,
            context_token_keys=("provider_token",),
            env_token_keys=("ATTIO_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "objectType": {
                    "type": "string",
                    "description": "The object type slug (e.g. people, companies)"
                },
                "matchingAttribute": {
                    "type": "string",
                    "description": "The attribute slug to match on for upsert (e.g. email_addresses for people, domains for companies)"
                },
                "values": {
                    "type": "string",
                    "description": "JSON object of attribute values (e.g. {\"email_addresses\":[{\"email_address\":\"test@example.com\"}]})"
                }
            },
            "required": ["objectType", "matchingAttribute", "values"]
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        object_type = parameters["objectType"].strip()
        matching_attribute = parameters["matchingAttribute"].strip()
        url = f"https://api.attio.com/v2/objects/{object_type}/records?matching_attribute={matching_attribute}"
        
        values: Dict[str, Any] = {}
        try:
            val = parameters["values"]
            if isinstance(val, str):
                values = json.loads(val)
            else:
                values = val
        except json.JSONDecodeError:
            values = {}
        
        json_body = {"data": {"values": values}}
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.put(url, headers=headers, json=json_body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")