from typing import Any, Dict, Optional
import httpx
import json
import re
from datetime import datetime
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class JiraCreateIssueLinkTool(BaseTool):
    name = "jira_create_issue_link"
    description = "Create a link relationship between two Jira issues"
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
            context_token_keys=("provider_token",),
            env_token_keys=("JIRA_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def _format_comment(self, comment: str | None) -> Optional[Dict[str, Any]]:
        if not comment or not comment.strip():
            return None
        return {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": comment.strip(),
                            }
                        ],
                    }
                ],
            }
        }

    async def _get_cloud_id(self, domain: str, access_token: str) -> str:
        url = "https://api.atlassian.com/oauth/token/accessible-resources"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            resources = response.json()
            for resource in resources:
                resource_url = resource.get("url", "")
                if resource_url == f"https://{domain}":
                    return resource["id"]
            raise ValueError(f"No accessible resource found for domain '{domain}'")

    async def _resolve_link_type(self, cloud_id: str, access_token: str, link_type: str) -> Dict[str, str]:
        url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/issueLinkType"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            all_types = data.get("issueLinkTypes", [])
            provided = link_type.strip().lower()
            for t in all_types:
                name = str(t.get("name", "")).lower()
                inward = str(t.get("inward", "")).lower()
                outward = str(t.get("outward", "")).lower()
                if provided in (name, inward, outward):
                    tid = t.get("id")
                    if tid is not None:
                        return {"id": str(tid)}
                    else:
                        return {"name": t.get("name", "")}
            if re.match(r"^\d+$", provided):
                return {"id": provided}
            available = "; ".join(
                f"{t.get('name')} (inward: {t.get('inward')}, outward: {t.get('outward')})"
                for t in all_types
            )
            raise ValueError(f'Unknown issue link type "{link_type}". Available: {available}')

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Your Jira domain (e.g., yourcompany.atlassian.net)",
                },
                "inwardIssueKey": {
                    "type": "string",
                    "description": "Jira issue key for the inward issue (e.g., PROJ-123)",
                },
                "outwardIssueKey": {
                    "type": "string",
                    "description": "Jira issue key for the outward issue (e.g., PROJ-456)",
                },
                "linkType": {
                    "type": "string",
                    "description": 'The type of link relationship (e.g., "Blocks", "Relates to", "Duplicates")',
                },
                "comment": {
                    "type": "string",
                    "description": "Optional comment to add to the issue link",
                },
            },
            "required": ["domain", "inwardIssueKey", "outwardIssueKey", "linkType"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        try:
            domain = parameters["domain"]
            inward_issue_key = parameters["inwardIssueKey"]
            outward_issue_key = parameters["outwardIssueKey"]
            link_type = parameters["linkType"]
            comment = parameters.get("comment")
            cloud_id = parameters.get("cloudId")

            if not cloud_id:
                cloud_id = await self._get_cloud_id(domain, access_token)

            resolved_type = await self._resolve_link_type(cloud_id, access_token, link_type)

            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            }

            body: Dict[str, Any] = {
                "type": resolved_type,
                "inwardIssue": {"key": inward_issue_key},
                "outwardIssue": {"key": outward_issue_key},
            }
            comment_body = self._format_comment(comment)
            if comment_body:
                body["comment"] = comment_body

            url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/issueLink"

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    link_id: Optional[str] = None
                    try:
                        link_data = response.json()
                        if link_data.get("id"):
                            link_id = str(link_data["id"])
                    except Exception:
                        location = response.headers.get("location") or response.headers.get("Location")
                        if location:
                            match = re.search(r"/issueLink/(\d+)", location)
                            if match:
                                link_id = match.group(1)

                    output_dict = {
                        "ts": datetime.utcnow().isoformat(),
                        "inwardIssue": inward_issue_key,
                        "outwardIssue": outward_issue_key,
                        "linkType": link_type,
                        "linkId": link_id,
                        "success": True,
                    }
                    return ToolResult(
                        success=True,
                        output=json.dumps(output_dict),
                        data=output_dict,
                    )
                else:
                    error_msg = f"Failed to create issue link ({response.status_code})"
                    try:
                        err = response.json()
                        if err.get("errorMessages"):
                            error_msg = ", ".join(err["errorMessages"])
                        elif err.get("message"):
                            error_msg = err["message"]
                    except Exception:
                        pass
                    return ToolResult(success=False, output="", error=error_msg)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")