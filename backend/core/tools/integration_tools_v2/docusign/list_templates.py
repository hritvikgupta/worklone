from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class DocusignListTemplatesTool(BaseTool):
    name = "docusign_list_templates"
    description = "List available templates in your DocuSign account"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="DOCUSIGN_ACCESS_TOKEN",
                description="DocuSign OAuth access token",
                env_var="DOCUSIGN_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "docusign",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("DOCUSIGN_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "searchText": {
                    "type": "string",
                    "description": "Search text to filter templates by name",
                },
                "count": {
                    "type": "string",
                    "description": "Maximum number of templates to return",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                tokeninfo_url = "https://account-d.docusign.com/oauth/tokeninfo"
                tokeninfo_resp = await client.get(tokeninfo_url, headers=headers)
                tokeninfo_resp.raise_for_status()
                tokeninfo_data = tokeninfo_resp.json()
                accounts = tokeninfo_data.get("accounts", [])
                if not accounts:
                    return ToolResult(success=False, output="", error="No DocuSign accounts found for this user.")
                account = next((acc for acc in accounts if acc.get("is_default") is True), accounts[0])
                account_id = account["account_id"]
                base_uri = account["base_uri"]
                templates_url = f"{base_uri.rstrip('/')}/restapi/v2.1/accounts/{account_id}/templates"
                
                query_params: Dict[str, str | int] = {}
                if search_text := parameters.get("searchText"):
                    query_params["search_text"] = search_text
                if count_str := parameters.get("count"):
                    try:
                        query_params["count"] = int(count_str)
                    except ValueError:
                        return ToolResult(success=False, output="", error="Invalid count value. Must be an integer.")
                
                resp = await client.get(templates_url, headers=headers, params=query_params)
                resp.raise_for_status()
                data = resp.json()
                envelope_templates = data.get("envelopeTemplates", [])
                templates = []
                for t in envelope_templates:
                    shared = t.get("shared")
                    templates.append({
                        "templateId": t.get("templateId"),
                        "name": t.get("name"),
                        "description": t.get("description"),
                        "shared": shared is True or shared == "true",
                        "created": t.get("created"),
                        "lastModified": t.get("lastModified"),
                    })
                output_data = {
                    "templates": templates,
                    "totalSetSize": int(data.get("totalSetSize", 0)),
                    "resultSetSize": int(data.get("resultSetSize", len(templates))),
                }
                import json
                return ToolResult(success=True, output=json.dumps(output_data), data=output_data)
            except httpx.HTTPStatusError as e:
                return ToolResult(success=False, output="", error=f"DocuSign API error ({e.response.status_code}): {e.response.text}")
            except Exception as e:
                return ToolResult(success=False, output="", error=f"API error: {str(e)}")