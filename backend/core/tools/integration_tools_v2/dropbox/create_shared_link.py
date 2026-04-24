from typing import Dict, Any
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class DropboxCreateSharedLinkTool(BaseTool):
    name = "dropbox_create_shared_link"
    description = "Create a shareable link for a file or folder in Dropbox"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="DROPBOX_ACCESS_TOKEN",
                description="Access token",
                env_var="DROPBOX_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "dropbox",
            context=context,
            context_token_keys=("dropbox_token",),
            env_token_keys=("DROPBOX_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path of the file or folder to share",
                },
                "requestedVisibility": {
                    "type": "string",
                    "description": "Visibility: public, team_only, or password",
                },
                "linkPassword": {
                    "type": "string",
                    "description": "Password for the shared link (only if visibility is password)",
                },
                "expires": {
                    "type": "string",
                    "description": "Expiration date in ISO 8601 format (e.g., 2025-12-31T23:59:59Z)",
                },
            },
            "required": ["path"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        url = "https://api.dropboxapi.com/2/sharing/create_shared_link_with_settings"

        body: Dict[str, Any] = {
            "path": parameters["path"],
        }

        settings: Dict[str, Any] = {}
        requested_visibility = parameters.get("requestedVisibility")
        if requested_visibility:
            settings["requested_visibility"] = {".tag": requested_visibility}
        link_password = parameters.get("linkPassword")
        if link_password:
            settings["link_password"] = link_password
        expires = parameters.get("expires")
        if expires:
            settings["expires"] = expires

        if settings:
            body["settings"] = settings

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                data = response.json()

                if response.status_code >= 400:
                    error_summary = data.get("error_summary", "")
                    if "shared_link_already_exists" in error_summary:
                        return ToolResult(
                            success=False,
                            output="",
                            error="A shared link already exists for this path. Use list_shared_links to get the existing link.",
                        )
                    error_msg = (
                        data.get("error_summary")
                        or data.get("error", {}).get("message", "")
                        or "Failed to create shared link"
                    )
                    return ToolResult(success=False, output="", error=error_msg)

                return ToolResult(
                    success=True,
                    output=response.text,
                    data={"sharedLink": data},
                )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")