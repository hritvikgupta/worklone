from typing import Any, Dict
import httpx
from datetime import datetime, timedelta, timezone
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class DocuSignListEnvelopesTool(BaseTool):
    name = "docusign_list_envelopes"
    description = "List envelopes from your DocuSign account with optional filters"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="DOCUSIGN_ACCESS_TOKEN",
                description="Access token",
                env_var="DOCUSIGN_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "docusign",
            context=context,
            context_token_keys=("provider_token",),
            env_token_keys=("DOCUSIGN_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "fromDate": {
                    "type": "string",
                    "description": "Start date filter (ISO 8601). Defaults to 30 days ago",
                },
                "toDate": {
                    "type": "string",
                    "description": "End date filter (ISO 8601)",
                },
                "envelopeStatus": {
                    "type": "string",
                    "description": "Filter by status: created, sent, delivered, completed, declined, voided",
                },
                "searchText": {
                    "type": "string",
                    "description": "Search text to filter envelopes",
                },
                "count": {
                    "type": "string",
                    "description": "Maximum number of envelopes to return (default: 25)",
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
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Get account info
                userinfo_url = "https://account-d.docusign.com/oauth/userinfo"
                userinfo_response = await client.get(userinfo_url, headers=headers)
                
                if userinfo_response.status_code != 200:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Failed to retrieve DocuSign account information: {userinfo_response.text}",
                    )
                
                userinfo = userinfo_response.json()
                accounts = userinfo.get("accounts", [])
                if not accounts:
                    return ToolResult(
                        success=False,
                        output="",
                        error="No DocuSign accounts found.",
                    )
                
                account = accounts[0]
                account_id = account["account_id"]
                base_uri = account["base_uri"].rstrip("/")
                
                # Build envelopes URL and params
                envelopes_url = f"{base_uri}/restapi/v2.1/accounts/{account_id}/envelopes"
                
                query_params: dict[str, str] = {}
                from_date = parameters.get("fromDate")
                if not from_date:
                    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
                    from_date = thirty_days_ago.strftime("%Y-%m-%d")
                if from_date:
                    query_params["from_date"] = from_date
                
                to_date = parameters.get("toDate")
                if to_date:
                    query_params["to_date"] = to_date
                
                envelope_status = parameters.get("envelopeStatus")
                if envelope_status:
                    query_params["status"] = envelope_status
                
                search_text = parameters.get("searchText")
                if search_text:
                    query_params["search_text"] = search_text
                
                count = parameters.get("count")
                if count:
                    query_params["count"] = count
                
                # List envelopes
                envelopes_response = await client.get(envelopes_url, headers=headers, params=query_params)
                
                if envelopes_response.status_code != 200:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Failed to list envelopes: {envelopes_response.text}",
                    )
                
                data = envelopes_response.json()
                envelopes_raw = data.get("envelopes", [])
                envelopes = [
                    {
                        "envelopeId": env.get("envelopeId"),
                        "status": env.get("status"),
                        "emailSubject": env.get("emailSubject"),
                        "sentDateTime": env.get("sentDateTime"),
                        "completedDateTime": env.get("completedDateTime"),
                        "createdDateTime": env.get("createdDateTime"),
                        "statusChangedDateTime": env.get("statusChangedDateTime"),
                    }
                    for env in envelopes_raw
                ]
                pagination = data.get("pagination", {})
                total_set_size = pagination.get("totalCount", 0)
                result_set_size = pagination.get("resultSetSize", len(envelopes))
                
                structured_data = {
                    "envelopes": envelopes,
                    "totalSetSize": total_set_size,
                    "resultSetSize": result_set_size,
                }
                
                return ToolResult(
                    success=True,
                    output=f"Successfully listed {len(envelopes)} envelopes.",
                    data=structured_data,
                )
                
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")