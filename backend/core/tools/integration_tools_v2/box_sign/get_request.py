from typing import Any, Dict, List
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class BoxSignGetRequestTool(BaseTool):
    name = "box_sign_get_request"
    description = "Get the details and status of a Box Sign request"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> List[CredentialRequirement]:
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
                "signRequestId": {
                    "type": "string",
                    "description": "The ID of the sign request to retrieve",
                }
            },
            "required": ["signRequestId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
        }

        sign_request_id = parameters["signRequestId"]
        url = f"https://api.box.com/2.0/sign_requests/{sign_request_id}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

            if response.status_code != 200:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("message") or f"Box Sign API error: {response.status_code}"
                except:
                    error_msg = f"Box Sign API error: {response.status_code} - {response.text}"
                return ToolResult(success=False, output="", error=error_msg)

            data = response.json()
            transformed = {
                "id": data.get("id") or "",
                "status": data.get("status") or "",
                "name": data.get("name"),
                "shortId": data.get("short_id"),
                "signers": [
                    {
                        "email": s.get("email"),
                        "role": s.get("role"),
                        "hasViewedDocument": s.get("has_viewed_document"),
                        "signerDecision": s.get("signer_decision"),
                        "embedUrl": s.get("embed_url"),
                        "order": s.get("order"),
                    }
                    for s in data.get("signers", [])
                ],
                "sourceFiles": [
                    {
                        "id": f.get("id"),
                        "type": f.get("type"),
                        "name": f.get("name"),
                    }
                    for f in data.get("source_files", [])
                ],
                "emailSubject": data.get("email_subject"),
                "emailMessage": data.get("email_message"),
                "daysValid": data.get("days_valid"),
                "createdAt": data.get("created_at"),
                "autoExpireAt": data.get("auto_expire_at"),
                "prepareUrl": data.get("prepare_url"),
                "senderEmail": data.get("sender_email"),
            }
            output_str = json.dumps(transformed, default=str)
            return ToolResult(success=True, output=output_str, data=transformed)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")