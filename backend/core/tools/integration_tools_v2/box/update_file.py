from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class BoxUpdateFileTool(BaseTool):
    name = "box_update_file"
    description = "Update file info in Box (rename, move, change description, add tags)"
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
        connection = await resolve_oauth_connection(
            "box",
            context=context,
            context_token_keys=("provider_token",),
            env_token_keys=("BOX_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def _build_body(self, parameters: dict) -> dict[str, Any]:
        body: dict[str, Any] = {}
        name = parameters.get("name")
        if name:
            body["name"] = name
        description = parameters.get("description")
        if description is not None:
            body["description"] = description
        parent_folder_id = parameters.get("parentFolderId")
        if parent_folder_id:
            body["parent"] = {"id": parent_folder_id.strip()}
        tags_str = parameters.get("tags")
        if tags_str:
            body["tags"] = [t.strip() for t in tags_str.split(",") if t.strip()]
        return body

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
                    "description": "New description for the file (max 256 characters)",
                },
                "parentFolderId": {
                    "type": "string",
                    "description": "Move the file to a different folder by specifying the folder ID",
                },
                "tags": {
                    "type": "string",
                    "description": "Comma-separated tags to set on the file",
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

        file_id = parameters["fileId"].strip()
        url = f"https://api.box.com/2.0/files/{file_id}"

        body = self._build_body(parameters)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.put(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")