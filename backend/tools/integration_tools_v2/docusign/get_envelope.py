from typing import Any, Dict
import httpx
import base64
import json
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class DocuSignGetEnvelopeTool(BaseTool):
    name = "docusign_get_envelope"
    description = "Get the details and status of a DocuSign envelope"
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

    def _get_userinfo_url(self, access_token: str) -> str:
        try:
            parts = access_token.split(".")
            if len(parts) != 3:
                raise ValueError("Invalid JWT")
            payload_b64 = parts[1] + "=" * ((4 - len(parts[1]) % 4) % 4)
            payload = base64.urlsafe_b64decode(payload_b64)
            payload_str = payload.decode("utf-8")
            data = json.loads(payload_str)
            iss = data.get("iss", "")
            if "account-d.docusign.com" in iss:
                return "https://account-d.docusign.com/oauth/userinfo"
            else:
                return "https://account.docusign.com/oauth/userinfo"
        except Exception:
            return "https://account-d.docusign.com/oauth/userinfo"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "envelopeId": {
                    "type": "string",
                    "description": "The envelope ID to retrieve",
                },
            },
            "required": ["envelopeId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {"Authorization": f"Bearer {access_token}"}

        userinfo_url = self._get_userinfo_url(access_token)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                userinfo_resp = await client.get(userinfo_url, headers=headers)

                if userinfo_resp.status_code != 200:
                    return ToolResult(
                        success=False, output="", error=f"Failed to fetch userinfo: {userinfo_resp.text}"
                    )

                userinfo = userinfo_resp.json()
                accounts = userinfo.get("accounts", [])
                if not accounts:
                    return ToolResult(success=False, output="", error="No accounts found in userinfo.")

                account = next(
                    (acc for acc in accounts if acc.get("is_default")), accounts[0]
                )
                account_id = account.get("account_id")
                base_uri = account.get("base_uri", "").rstrip("/")
                if not account_id or not base_uri:
                    return ToolResult(
                        success=False,
                        output="",
                        error="Invalid account information.",
                    )

                envelope_id = parameters["envelopeId"]
                envelope_url = f"{base_uri}/v2.1/accounts/{account_id}/envelopes/{envelope_id}"

                env_resp = await client.get(envelope_url, headers=headers)

                if env_resp.status_code == 200:
                    data = env_resp.json()
                    output_data = {
                        "envelopeId": data.get("envelopeId"),
                        "status": data.get("status"),
                        "emailSubject": data.get("emailSubject"),
                        "sentDateTime": data.get("sentDateTime"),
                        "completedDateTime": data.get("completedDateTime"),
                        "createdDateTime": data.get("createdDateTime"),
                        "statusChangedDateTime": data.get("statusChangedDateTime"),
                        "voidedReason": data.get("voidedReason"),
                        "signerCount": len(data.get("recipients", {}).get("signers", [])),
                        "documentCount": len(data.get("envelopeDocuments", [])),
                    }
                    return ToolResult(
                        success=True, output=json.dumps(output_data), data=output_data
                    )
                else:
                    return ToolResult(
                        success=False, output="", error=f"Failed to get envelope: {env_resp.text}"
                    )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")