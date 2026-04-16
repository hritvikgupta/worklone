from typing import Any, Dict
import httpx
import base64
import json
import re
import urllib.parse
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class SalesforceGetAccountsTool(BaseTool):
    name = "salesforce_get_accounts"
    description = "Retrieve accounts from Salesforce CRM"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="SALESFORCE_ACCESS_TOKEN",
                description="Access token",
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

    def _get_instance_url(self, id_token: str | None, instance_url: str | None) -> str | None:
        if instance_url:
            return instance_url
        if not id_token:
            return None
        try:
            payload = id_token.split(".")[1]
            padding_len = (4 - len(payload) % 4) % 4
            payload += "=" * padding_len
            decoded_bytes = base64.urlsafe_b64decode(payload)
            decoded = json.loads(decoded_bytes.decode("utf-8"))
            profile = decoded.get("profile")
            if profile:
                match = re.match(r"^https://[^/]+", profile)
                if match:
                    return match.group(0)
            sub = decoded.get("sub")
            if sub:
                match = re.match(r"^https://[^/]+", sub)
                if match and match.group(0) != "https://login.salesforce.com":
                    return match.group(0)
        except Exception:
            pass
        return None

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "string",
                    "description": "Maximum number of results (default: 100, max: 2000)",
                },
                "fields": {
                    "type": "string",
                    "description": "Comma-separated field API names (e.g., \"Id,Name,Industry,Phone\")",
                },
                "orderBy": {
                    "type": "string",
                    "description": "Field and direction for sorting (e.g., \"Name ASC\" or \"CreatedDate DESC\")",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        id_token = context.get("idToken") if context else None
        instance_url_from_context = context.get("instanceUrl") if context else None
        instance_url = self._get_instance_url(id_token, instance_url_from_context)
        
        if not instance_url:
            return ToolResult(success=False, output="", error="Salesforce instance URL is required but not provided.")
        
        limit_str = parameters.get("limit")
        limit = int(limit_str) if limit_str else 100
        fields = parameters.get("fields", "Id,Name,Type,Industry,BillingCity,BillingState,BillingCountry,Phone,Website")
        order_by = parameters.get("orderBy", "Name ASC")
        
        query = f"SELECT {fields} FROM Account ORDER BY {order_by} LIMIT {limit}"
        encoded_query = urllib.parse.quote(query)
        url = f"{instance_url}/services/data/v59.0/query?q={encoded_query}"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    try:
                        error_data = response.json()
                        if isinstance(error_data, list) and len(error_data) > 0 and isinstance(error_data[0], dict):
                            error_msg = error_data[0].get("message", str(error_data[0]))
                        elif isinstance(error_data, dict):
                            error_msg = error_data.get("message", response.text)
                        else:
                            error_msg = response.text
                    except Exception:
                        error_msg = response.text
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")