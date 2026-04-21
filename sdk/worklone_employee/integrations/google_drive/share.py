from typing import Any, Dict
import httpx
import base64
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class GoogleDriveShareTool(BaseTool):
    name = "google_drive_share"
    description = "Share a file with a user, group, domain, or make it public"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GOOGLE_DRIVE_ACCESS_TOKEN",
                description="Google Drive access token",
                env_var="GOOGLE_DRIVE_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "google-drive",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("GOOGLE_DRIVE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "fileId": {
                    "type": "string",
                    "description": "The ID of the file to share",
                },
                "type": {
                    "type": "string",
                    "description": "Type of grantee: user, group, domain, or anyone",
                },
                "role": {
                    "type": "string",
                    "description": "Permission role: owner (transfer ownership), organizer (shared drive only), fileOrganizer (shared drive only), writer (edit), commenter (view and comment), reader (view only)",
                },
                "email": {
                    "type": "string",
                    "description": "Email address of the user or group (required for type=user or type=group)",
                },
                "domain": {
                    "type": "string",
                    "description": "Domain to share with (required for type=domain)",
                },
                "transferOwnership": {
                    "type": "boolean",
                    "description": "Required when role is owner. Transfers ownership to the specified user.",
                },
                "moveToNewOwnersRoot": {
                    "type": "boolean",
                    "description": "When transferring ownership, move the file to the new owner's My Drive root folder.",
                },
                "sendNotification": {
                    "type": "boolean",
                    "description": "Whether to send an email notification (default: true)",
                },
                "emailMessage": {
                    "type": "string",
                    "description": "Custom message to include in the notification email",
                },
            },
            "required": ["fileId", "type", "role"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        file_id = parameters.get("fileId", "").strip()
        url = f"https://www.googleapis.com/drive/v3/files/{file_id}/permissions"
        
        query_params: Dict[str, str] = {
            "supportsAllDrives": "true",
        }
        if parameters.get("transferOwnership"):
            query_params["transferOwnership"] = "true"
        if parameters.get("moveToNewOwnersRoot"):
            query_params["moveToNewOwnersRoot"] = "true"
        send_notification = parameters.get("sendNotification")
        if send_notification is not None:
            query_params["sendNotificationEmail"] = str(send_notification).lower()
        email_message = parameters.get("emailMessage")
        if email_message:
            query_params["emailMessage"] = email_message
        
        body: Dict[str, Any] = {
            "type": parameters["type"],
            "role": parameters["role"],
        }
        email = parameters.get("email")
        if email:
            body["emailAddress"] = email.strip()
        domain = parameters.get("domain")
        if domain:
            body["domain"] = domain.strip()
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    headers=headers,
                    json=body,
                    params=query_params,
                )
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")