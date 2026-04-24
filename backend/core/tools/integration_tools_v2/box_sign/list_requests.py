from typing import Any, Dict
import httpx
import json
from urllib.parse import urlencode
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class BoxSignListRequestsTool(BaseTool):
    name = "box_sign_list_requests"
    description = "List all Box Sign requests"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="BOX_ACCESS_TOKEN",
                description="OAuth access token for Box API",
                env_var="BOX_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection("box_sign",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("BOX_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "number",
                    "description": "Maximum number of sign requests to return (max 1000)",
                },
                "marker": {
                    "type": "string",
                    "description": "Pagination marker from a previous response",
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
        
        query_dict: Dict[str, Any] = {}
        limit = parameters.get("limit")
        if limit is not None:
            query_dict["limit"] = limit
        marker = parameters.get("marker")
        if marker:
            query_dict["marker"] = marker
        qs = urlencode(query_dict)
        url = f"https://api.box.com/2.0/sign_requests{'?' + qs if qs else ''}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    try:
                        data = response.json()
                        entries = data.get("entries", [])
                        sign_requests = []
                        for req in entries:
                            signers = [
                                {
                                    "email": s.get("email"),
                                    "role": s.get("role"),
                                    "hasViewedDocument": s.get("has_viewed_document"),
                                    "signerDecision": s.get("signer_decision"),
                                    "embedUrl": s.get("embed_url"),
                                    "order": s.get("order"),
                                }
                                for s in req.get("signers", [])
                            ]
                            source_files = [
                                {
                                    "id": f.get("id"),
                                    "type": f.get("type"),
                                    "name": f.get("name"),
                                }
                                for f in req.get("source_files", [])
                            ]
                            sign_req = {
                                "id": req.get("id", ""),
                                "status": req.get("status", ""),
                                "name": req.get("name"),
                                "shortId": req.get("short_id"),
                                "signers": signers,
                                "sourceFiles": source_files,
                                "emailSubject": req.get("email_subject"),
                                "emailMessage": req.get("email_message"),
                                "daysValid": req.get("days_valid"),
                                "createdAt": req.get("created_at"),
                                "autoExpireAt": req.get("auto_expire_at"),
                                "prepareUrl": req.get("prepare_url"),
                                "senderEmail": req.get("sender_email"),
                            }
                            sign_requests.append(sign_req)
                        output_data = {
                            "signRequests": sign_requests,
                            "count": len(entries),
                            "nextMarker": data.get("next_marker"),
                        }
                        output_str = json.dumps(output_data)
                        return ToolResult(success=True, output=output_str, data=output_data)
                    except Exception as parse_err:
                        return ToolResult(
                            success=False, output="", error=f"Failed to parse response: {str(parse_err)}"
                        )
                else:
                    try:
                        err_data = response.json()
                        error_msg = err_data.get("message", f"Box Sign API error: {response.status_code}")
                    except Exception:
                        error_msg = response.text or f"HTTP error: {response.status_code}"
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")