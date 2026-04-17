from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleDriveUpdateTool(BaseTool):
    name = "google_drive_update"
    description = "Update file metadata in Google Drive (rename, move, star, add description)"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GOOGLE_DRIVE_ACCESS_TOKEN",
                description="Access token",
                env_var="GOOGLE_DRIVE_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "google-drive",
            context=context,
            context_token_keys=("access_token",),
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
                    "description": "The ID of the file to update",
                },
                "name": {
                    "type": "string",
                    "description": "New name for the file",
                },
                "description": {
                    "type": "string",
                    "description": "New description for the file",
                },
                "addParents": {
                    "type": "string",
                    "description": "Comma-separated list of parent folder IDs to add (moves file to these folders)",
                },
                "removeParents": {
                    "type": "string",
                    "description": "Comma-separated list of parent folder IDs to remove",
                },
                "starred": {
                    "type": "boolean",
                    "description": "Whether to star or unstar the file",
                },
            },
            "required": ["fileId"],
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
        url = f"https://www.googleapis.com/drive/v3/files/{file_id}"

        params_dict: Dict[str, str] = {
            "fields": "id,kind,name,mimeType,description,starred,webViewLink,parents,modifiedTime",
            "supportsAllDrives": "true",
        }

        add_parents = parameters.get("addParents")
        if add_parents:
            params_dict["addParents"] = str(add_parents).strip()

        remove_parents = parameters.get("removeParents")
        if remove_parents:
            params_dict["removeParents"] = str(remove_parents).strip()

        body: Dict[str, Any] = {}
        name = parameters.get("name")
        if name is not None:
            body["name"] = name
        description = parameters.get("description")
        if description is not None:
            body["description"] = description
        starred = parameters.get("starred")
        if starred is not None:
            body["starred"] = starred

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(url, headers=headers, params=params_dict, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")