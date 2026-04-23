from typing import Any, Dict
import httpx
import base64
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class DropboxDownloadTool(BaseTool):
    name = "dropbox_download"
    description = "Download a file from Dropbox with metadata and content"
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
            context_token_keys=("provider_token",},
            env_token_keys=("DROPBOX_ACCESS_TOKEN",},
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
                    "description": "The path of the file to download (e.g., /folder/document.pdf)",
                },
            },
            "required": ["path"],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        path = parameters["path"]
        url = "https://content.dropboxapi.com/2/files/download"
        arg_json = json.dumps({"path": path}, separators=(",", ":"))
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/octet-stream",
            "Dropbox-API-Arg": arg_json,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers)

                if response.status_code != 200:
                    error_text = response.text
                    return ToolResult(success=False, output="", error=error_text or "Failed to download file")

                api_result_header = (
                    response.headers.get("dropbox-api-result")
                    or response.headers.get("Dropbox-API-Result")
                )
                metadata = json.loads(api_result_header) if api_result_header else None
                content_type = response.headers.get("content-type", "application/octet-stream")
                content = response.content
                base64_content = base64.b64encode(content).decode("utf-8")
                size = len(content)
                resolved_name = (
                    metadata["name"]
                    if metadata and isinstance(metadata, dict) and "name" in metadata
                    else (path.split("/")[-1] if path.split("/") else "download")
                )

                temporary_link = None
                try:
                    link_url = "https://api.dropboxapi.com/2/files/get_temporary_link"
                    link_headers = {
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                    }
                    link_response = await client.post(
                        link_url, headers=link_headers, json={"path": path}
                    )
                    if link_response.status_code == 200:
                        link_data = link_response.json()
                        temporary_link = link_data["link"]
                except Exception:
                    pass

                output_data = {
                    "file": {
                        "name": resolved_name,
                        "mimeType": content_type,
                        "data": base64_content,
                        "size": size,
                    },
                    "content": base64_content,
                    "metadata": metadata,
                    "temporaryLink": temporary_link,
                }
                return ToolResult(success=True, output=base64_content, data=output_data)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")