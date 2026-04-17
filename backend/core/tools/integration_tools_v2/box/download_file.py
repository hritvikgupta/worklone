from typing import Any, Dict
import httpx
import base64
import re
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class BoxDownloadFileTool(BaseTool):
    name = "box_download_file"
    description = "Download a file from Box"
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
                "fileId": {
                    "type": "string",
                    "description": "The ID of the file to download",
                }
            },
            "required": ["fileId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
        }

        file_id = parameters["fileId"].strip()
        url = f"https://api.box.com/2.0/files/{file_id}/content"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code == 202:
                    retry_after = response.headers.get("retry-after", "a few")
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"File is not yet ready for download. Retry after {retry_after} seconds.",
                    )

                if not (200 <= response.status_code < 300):
                    error_text = response.text
                    return ToolResult(
                        success=False,
                        output="",
                        error=error_text or f"Failed to download file: {response.status_code}",
                    )

                content_type = response.headers.get("content-type", "application/octet-stream")
                content_disposition = response.headers.get("content-disposition")
                file_name = "download"

                if content_disposition:
                    match = re.search(r'filename[^;=\n]*=(([\'"]).*?\2|[^;\n]*)', content_disposition)
                    if match and match.group(1):
                        file_name = match.group(1).replace("'", "").replace('"', "")

                buffer = response.content
                data_b64 = base64.b64encode(buffer).decode("utf-8")
                size = len(buffer)

                output_data = {
                    "file": {
                        "name": file_name,
                        "mimeType": content_type,
                        "data": data_b64,
                        "size": size,
                    },
                    "content": data_b64,
                }

                return ToolResult(success=True, output=data_b64, data=output_data)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")