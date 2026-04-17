from typing import Any, Dict, List, Optional
import httpx
import base64
import json
from datetime import datetime
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class JiraGetAttachmentsTool(BaseTool):
    name = "jira_get_attachments"
    description = "Get all attachments from a Jira issue"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="JIRA_ACCESS_TOKEN",
                description="OAuth access token for Jira",
                env_var="JIRA_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "jira",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("JIRA_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Your Jira domain (e.g., yourcompany.atlassian.net)",
                },
                "issueKey": {
                    "type": "string",
                    "description": "Jira issue key to get attachments from (e.g., PROJ-123)",
                },
                "includeAttachments": {
                    "type": "boolean",
                    "description": "Download attachment file contents and include them as files in the output",
                },
                "cloudId": {
                    "type": "string",
                    "description": "Jira Cloud ID for the instance. If not provided, it will be fetched using the domain.",
                },
            },
            "required": ["domain", "issueKey"],
        }

    def _transform_attachment(self, att: Dict[str, Any]) -> Dict[str, Any]:
        author_obj = att.get("author")
        author_name = "Unknown"
        if author_obj:
            author_name = author_obj.get("displayName") or author_obj.get("accountId") or "Unknown"
        created_raw = att.get("created", "")
        created = created_raw
        if isinstance(created_raw, (int, float)):
            created = datetime.fromtimestamp(created_raw / 1000).isoformat()
        return {
            "id": att.get("id", ""),
            "filename": att.get("filename", ""),
            "mimeType": att.get("mimeType", ""),
            "size": att.get("size", 0),
            "content": att.get("content", ""),
            "thumbnail": att.get("thumbnail"),
            "author": author_obj,
            "authorName": author_name,
            "created": created,
        }

    async def _get_jira_cloud_id(self, domain: str, access_token: str) -> str:
        url = "https://api.atlassian.com/oauth/token/accessible-resources"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                try:
                    err_data = resp.json()
                    msg = ", ".join(err_data.get("errorMessages", [])) or err_data.get("message", resp.text)
                except Exception:
                    msg = resp.text
                raise ValueError(f"Failed to get accessible resources ({resp.status_code}): {msg}")
            resources: List[Dict[str, Any]] = resp.json()
            for resource in resources:
                resource_url = resource.get("url", "").rstrip("/")
                if domain in resource_url:
                    return resource["id"]
            avail_urls = [r.get("url", "") for r in resources]
            raise ValueError(f"No matching cloud ID for domain '{domain}'. Available URLs: {avail_urls}")

    async def _download_jira_attachments(self, attachments: List[Dict[str, Any]], access_token: str) -> List[Dict[str, Any]]:
        files: List[Dict[str, Any]] = []
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            for att in attachments:
                content_url = att.get("content")
                if not content_url:
                    continue
                try:
                    resp = await client.get(content_url, headers=headers)
                    if resp.status_code == 200:
                        data_b64 = base64.b64encode(resp.content).decode("utf-8")
                        files.append({
                            "name": att["filename"],
                            "mimeType": att["mimeType"],
                            "data": data_b64,
                            "size": att["size"],
                        })
                except Exception:
                    continue
        return files

    async def execute(self, parameters: Dict[str, Any], context: dict | None = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        domain: str = parameters["domain"]
        issue_key: str = parameters["issueKey"]
        include_attachments: bool = parameters.get("includeAttachments", False)
        cloud_id: Optional[str] = parameters.get("cloudId")

        if cloud_id is None:
            try:
                cloud_id = await self._get_jira_cloud_id(domain, access_token)
            except ValueError as e:
                return ToolResult(success=False, output="", error=str(e))

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/issue/{issue_key}?fields=attachment"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code != 200:
                    try:
                        err_data = resp.json()
                        error_msg = ", ".join(err_data.get("errorMessages", [])) or err_data.get("message", resp.text)
                    except Exception:
                        error_msg = resp.text
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Failed to get attachments from Jira issue ({resp.status_code}): {error_msg}",
                    )
                data = resp.json()
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")

        attachments_raw = data.get("fields", {}).get("attachment", [])
        attachments = [self._transform_attachment(att) for att in attachments_raw]

        output_data: Dict[str, Any] = {
            "ts": datetime.now().isoformat(),
            "issueKey": issue_key,
            "attachments": attachments,
        }
        if include_attachments:
            files = await self._download_jira_attachments(attachments, access_token)
            if files:
                output_data["files"] = files

        return ToolResult(success=True, output=json.dumps(output_data), data=output_data)