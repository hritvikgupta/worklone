from typing import Any, Dict
import httpx
import base64
import json
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class SlackDownloadTool(BaseTool):
    name = "slack_download"
    description = "Download a file from Slack"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="SLACK_ACCESS_TOKEN",
                description="Slack OAuth access token or bot token",
                env_var="SLACK_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "slack",
            context=context,
            context_token_keys=("provider_token",),
            env_token_keys=("SLACK_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "authMethod": {
                    "type": "string",
                    "description": "Authentication method: oauth or bot_token",
                },
                "botToken": {
                    "type": "string",
                    "description": "Bot token for Custom Bot",
                },
                "accessToken": {
                    "type": "string",
                    "description": "OAuth access token or bot token for Slack API",
                },
                "fileId": {
                    "type": "string",
                    "description": "The ID of the file to download",
                },
                "fileName": {
                    "type": "string",
                    "description": "Optional filename override",
                },
            },
            "required": ["fileId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        file_id: str = parameters["fileId"]
        file_name_param: str | None = parameters.get("fileName")
        candidate_token: str | None = parameters.get("accessToken") or parameters.get("botToken")

        access_token = await self._resolve_access_token(context)

        if candidate_token and not self._is_placeholder_token(candidate_token):
            access_token = candidate_token

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        auth_headers = {
            "Authorization": f"Bearer {access_token}",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                info_url = f"https://slack.com/api/files.info?file={file_id}"
                info_response = await client.get(info_url, headers=auth_headers)

                if info_response.status_code != 200:
                    try:
                        error_data = info_response.json()
                        error_msg = error_data.get("error") or info_response.text
                    except Exception:
                        error_msg = info_response.text
                    return ToolResult(success=False, output="", error=error_msg)

                try:
                    data = info_response.json()
                except Exception:
                    return ToolResult(success=False, output="", error="Invalid JSON from files.info")

                if not data.get("ok", False):
                    error_msg = data.get("error", "Slack API error")
                    return ToolResult(success=False, output="", error=error_msg)

                file_info = data.get("file")
                if not file_info:
                    return ToolResult(success=False, output="", error="No file info returned")

                url_private = file_info.get("url_private")
                if not url_private:
                    return ToolResult(success=False, output="", error="File does not have a download URL")

                resolved_file_name = file_name_param or file_info.get("name") or "download"
                mime_type = file_info.get("mimetype") or "application/octet-stream"

                download_response = await client.get(url_private, headers=auth_headers)

                if download_response.status_code != 200:
                    return ToolResult(success=False, output="", error="Failed to download file content")

                file_bytes = await download_response.aread()
                base64_data = base64.b64encode(file_bytes).decode("utf-8")
                size = len(file_bytes)

                output_data = {
                    "file": {
                        "name": resolved_file_name,
                        "mimeType": mime_type,
                        "data": base64_data,
                        "size": size,
                    }
                }

                return ToolResult(success=True, output=json.dumps(output_data), data=output_data)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")