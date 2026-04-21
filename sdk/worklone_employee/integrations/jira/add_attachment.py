from typing import Any, Dict
import httpx
import json
from datetime import datetime
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class JiraAddAttachmentTool(BaseTool):
    name = "jira_add_attachment"
    description = "Add attachments to a Jira issue"
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
            context_token_keys=("accessToken", "jira_token", "access_token"),
            env_token_keys=("JIRA_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    async def _get_cloud_id(self, domain: str, access_token: str) -> str:
        url = "https://api.atlassian.com/oauth/token/accessible-resources"
        headers = {"Authorization": f"Bearer {access_token}"}
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                resources = response.json()
                domain_lower = domain.lower().rstrip("/")
                for resource in resources:
                    resource_url = resource.get("url", "").lower().rstrip("/")
                    if domain_lower in resource_url or resource_url.endswith(domain_lower):
                        return resource["id"]
                raise ValueError(f"No matching cloud ID found for domain '{domain}'")
        except Exception as e:
            raise ValueError(f"Failed to fetch cloud ID: {str(e)}")

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
                    "description": "Jira issue key to add attachments to (e.g., PROJ-123)",
                },
                "files": {
                    "type": "array",
                    "description": "Files to attach to the Jira issue",
                },
                "cloudId": {
                    "type": "string",
                    "description": "Jira Cloud ID for the instance. If not provided, it will be fetched using the domain.",
                },
            },
            "required": ["domain", "issueKey", "files"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        domain: str = parameters["domain"]
        issue_key: str = parameters["issueKey"]
        files: list = parameters["files"]
        if not files or len(files) == 0:
            return ToolResult(success=False, output="", error="No valid files provided for upload")
        
        cloud_id: str | None = parameters.get("cloudId")
        if not cloud_id:
            cloud_id = await self._get_cloud_id(domain, access_token)
        
        url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/issue/{issue_key}/attachments"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Atlassian-Token": "no-check",
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                multipart_files = []
                for file_info in files:
                    name = file_info.get("name")
                    if not name:
                        raise ValueError("File missing name")
                    file_type = file_info.get("type") or file_info.get("mimeType") or "application/octet-stream"
                    file_url = file_info.get("url")
                    if not file_url:
                        raise ValueError("File missing url")
                    file_resp = await client.get(file_url)
                    file_resp.raise_for_status()
                    content = await file_resp.aread()
                    multipart_files.append(("file", (name, content, file_type)))
                
                response = await client.post(url, headers=headers, files=multipart_files)
                
                if response.status_code in [200, 201, 204]:
                    try:
                        jira_attachments = response.json()
                    except Exception:
                        jira_attachments = []
                    attachments_list = jira_attachments if isinstance(jira_attachments, list) else []
                    attachments = [
                        {
                            "id": att.get("id", ""),
                            "filename": att.get("filename", ""),
                            "mimeType": att.get("mimeType", ""),
                            "size": att.get("size", 0),
                            "content": att.get("content", ""),
                        }
                        for att in attachments_list
                    ]
                    attachment_ids = [att.get("id") for att in attachments_list if att.get("id")]
                    output_dict = {
                        "ts": datetime.utcnow().isoformat(),
                        "issueKey": issue_key,
                        "attachments": attachments,
                        "attachmentIds": attachment_ids,
                        "files": files,
                    }
                    return ToolResult(success=True, output=json.dumps(output_dict), data=output_dict)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")