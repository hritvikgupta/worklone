from typing import Any, Dict
import httpx
import base64
import json
from datetime import datetime
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ConfluenceUploadAttachmentTool(BaseTool):
    name = "confluence_upload_attachment"
    description = "Upload a file as an attachment to a Confluence page."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="CONFLUENCE_ACCESS_TOKEN",
                description="OAuth access token for Confluence",
                env_var="CONFLUENCE_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "confluence",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("CONFLUENCE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    async def _get_cloud_id(self, domain: str, access_token: str) -> str:
        userinfo_url = "https://api.atlassian.com/oauth/token/userinfo"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(userinfo_url, headers={"Authorization": f"Bearer {access_token}"})
                resp.raise_for_status()
                data = resp.json()
            confluence_account = next(
                (
                    acc
                    for acc in data.get("accounts", [])
                    if acc.get("product") == "confluence" and acc.get("name") == domain
                ),
                None,
            )
            if not confluence_account:
                raise ValueError(f"No Confluence account found for domain '{domain}'")
            return confluence_account["id"]
        except httpx.HTTPStatusError as e:
            raise ValueError(f"Failed to fetch cloud ID: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise ValueError(f"Error fetching cloud ID: {str(e)}")

    def _process_file(self, file_param: Any, file_name: str | None) -> tuple[bytes, str, str]:
        if isinstance(file_param, dict):
            data_str = file_param.get("data") or file_param.get("content")
            if not data_str:
                raise ValueError("File data missing")
            content = base64.b64decode(data_str)
            filename = file_param.get("name") or file_name or "attachment"
            mime_type = file_param.get("type", "application/octet-stream")
        elif isinstance(file_param, str):
            content = base64.b64decode(file_param)
            filename = file_name or "attachment"
            mime_type = "application/octet-stream"
        else:
            raise ValueError("Invalid file format: must be base64 string or dict with 'data'")
        if not content:
            raise ValueError("File content is empty")
        return content, mime_type, filename

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Your Confluence domain (e.g., yourcompany.atlassian.net)",
                },
                "pageId": {
                    "type": "string",
                    "description": "Confluence page ID to attach the file to",
                },
                "file": {
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "string",
                            "description": "The base64 encoded file content",
                        },
                        "name": {
                            "type": "string",
                            "description": "Optional file name",
                        },
                        "type": {
                            "type": "string",
                            "description": "Optional MIME type",
                        },
                    },
                    "required": ["data"],
                },
                "fileName": {
                    "type": "string",
                    "description": "Optional custom file name for the attachment",
                },
                "comment": {
                    "type": "string",
                    "description": "Optional comment to add to the attachment",
                },
                "cloudId": {
                    "type": "string",
                    "description": "Confluence Cloud ID for the instance. If not provided, it will be fetched using the domain.",
                },
            },
            "required": ["domain", "pageId", "file"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        domain = parameters.get("domain")
        page_id = parameters.get("pageId")
        file_param = parameters.get("file")
        file_name = parameters.get("fileName")
        comment = parameters.get("comment")
        cloud_id = parameters.get("cloudId")

        if not domain or not page_id or not file_param:
            return ToolResult(
                success=False, output="", error="Missing required parameters: domain, pageId, file"
            )

        try:
            if not cloud_id:
                cloud_id = await self._get_cloud_id(domain, access_token)

            content, mime_type, upload_filename = self._process_file(file_param, file_name)

            url = f"https://api.atlassian.com/ex/confluence/{cloud_id}/wiki/rest/api/content/{page_id}/child/attachment"

            files = {"file": (upload_filename, content, mime_type)}
            data: Dict[str, str] = {"minorEdit": "false"}
            if comment:
                data["comment"] = comment

            headers = {
                "Authorization": f"Bearer {access_token}",
                "X-Atlassian-Token": "nocheck",
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, files=files, data=data)

            if response.status_code in [200, 201]:
                resp_data = response.json()
                attachment = resp_data.get("results", [None])[0] or resp_data
                output_data = {
                    "ts": datetime.utcnow().isoformat(),
                    "attachmentId": attachment.get("id", ""),
                    "title": attachment.get("title", ""),
                    "fileSize": attachment.get("extensions", {}).get("fileSize", 0),
                    "mediaType": attachment.get("extensions", {}).get("mediaType", mime_type),
                    "downloadUrl": attachment.get("_links", {}).get("download", ""),
                    "pageId": page_id,
                }
                return ToolResult(
                    success=True, output=json.dumps(output_data), data=output_data
                )
            else:
                try:
                    error_data = response.json()
                except:
                    error_data = {}
                error_msg = (
                    error_data.get("message")
                    or error_data.get("errorMessage")
                    or f"Failed to upload attachment to Confluence ({response.status_code})"
                )
                return ToolResult(success=False, output="", error=error_msg)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")