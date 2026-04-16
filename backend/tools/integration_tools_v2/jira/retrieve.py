from typing import Any, Dict, List, Optional
import httpx
import asyncio
import json
import base64
from datetime import datetime, timezone
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class JiraRetrieveTool(BaseTool):
    name = "jira_retrieve"
    description = "Retrieve detailed information about a specific Jira issue"
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
                    "description": "Jira issue key to retrieve (e.g., PROJ-123)",
                },
                "includeAttachments": {
                    "type": "boolean",
                    "description": "Download attachment file contents and include them as files in the output",
                },
            },
            "required": ["domain", "issueKey"],
        }

    def _extract_adf_text(self, adf: Any) -> str:
        if not adf:
            return ""
        def recurse(node: Any) -> str:
            if isinstance(node, str):
                return node
            if not isinstance(node, dict):
                return ""
            node_type = node.get("type")
            if node_type == "text":
                return node.get("text", "")
            content = node.get("content", [])
            text = "".join(recurse(child) for child in content)
            if node_type in ["paragraph", "heading"]:
                text += "\n"
            return text
        return recurse(adf)

    def _transform_user(self, user: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not user:
            return None
        return {
            "accountId": user.get("accountId", ""),
            "displayName": user.get("displayName", ""),
            "avatarUrls": user.get("avatarUrls", {}),
        }

    def _transform_issue_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        fields = data.get("fields", {})
        status = fields.get("status", {})
        status_category = status.get("statusCategory")
        issue_type = fields.get("issuetype", {})
        project = fields.get("project", {})
        priority = fields.get("priority")
        resolution = fields.get("resolution")
        time_tracking = fields.get("timetracking")
        parent = fields.get("parent")
        issue_links = fields.get("issuelinks", [])
        subtasks = fields.get("subtasks", [])
        votes = fields.get("votes")
        watches = fields.get("watches") or fields.get("watcher")
        comments_list = fields.get("comment", {}).get("comments", fields.get("comment", [])) or []
        worklogs_list = fields.get("worklog", {}).get("worklogs", fields.get("worklog", [])) or []
        attachments_list = fields.get("attachment", [])

        def get_author_name(author: Optional[Dict[str, Any]]) -> str:
            if not author:
                return "Unknown"
            return author.get("displayName") or author.get("accountId") or "Unknown"

        transformed_comments = []
        for c in comments_list:
            transformed_comments.append({
                "id": c.get("id", ""),
                "body": self._extract_adf_text(c.get("body")),
                "author": self._transform_user(c.get("author")),
                "authorName": get_author_name(c.get("author")),
                "updateAuthor": self._transform_user(c.get("updateAuthor")),
                "created": c.get("created", ""),
                "updated": c.get("updated", ""),
                "visibility": {
                    "type": c.get("visibility", {}).get("type", ""),
                    "value": c.get("visibility", {}).get("value", ""),
                } if c.get("visibility") else None,
            })

        transformed_worklogs = []
        for w in worklogs_list:
            transformed_worklogs.append({
                "id": w.get("id", ""),
                "author": self._transform_user(w.get("author")),
                "authorName": get_author_name(w.get("author")),
                "updateAuthor": self._transform_user(w.get("updateAuthor")),
                "comment": self._extract_adf_text(w.get("comment")) if w.get("comment") else None,
                "started": w.get("started", ""),
                "timeSpent": w.get("timeSpent", ""),
                "timeSpentSeconds": w.get("timeSpentSeconds", 0),
                "created": w.get("created", ""),
                "updated": w.get("updated", ""),
            })

        transformed_attachments = []
        for att in attachments_list:
            transformed_attachments.append({
                "id": att.get("id", ""),
                "filename": att.get("filename", ""),
                "mimeType": att.get("mimeType", ""),
                "size": att.get("size", 0),
                "content": att.get("content", ""),
                "thumbnail": att.get("thumbnail"),
                "author": self._transform_user(att.get("author")),
                "authorName": get_author_name(att.get("author")),
                "created": att.get("created", ""),
            })

        transformed_components = [
            {
                "id": c.get("id", ""),
                "name": c.get("name", ""),
                "description": c.get("description"),
            }
            for c in fields.get("components", [])
        ]

        transformed_fix_versions = [
            {
                "id": v.get("id", ""),
                "name": v.get("name", ""),
                "released": v.get("released"),
                "releaseDate": v.get("releaseDate"),
            }
            for v in fields.get("fixVersions", [])
        ]

        transformed_issue_links = []
        for link in issue_links:
            transformed_issue_links.append({
                "id": link.get("id", ""),
                "type": {
                    "id": link.get("type", {}).get("id", ""),
                    "name": link.get("type", {}).get("name", ""),
                    "inward": link.get("type", {}).get("inward", ""),
                    "outward": link.get("type", {}).get("outward", ""),
                },
                "inwardIssue": {
                    "id": link.get("inwardIssue", {}).get("id", ""),
                    "key": link.get("inwardIssue", {}).get("key", ""),
                    "statusName": link.get("inwardIssue", {}).get("fields", {}).get("status", {}).get("name"),
                    "summary": link.get("inwardIssue", {}).get("fields", {}).get("summary"),
                } if link.get("inwardIssue") else None,
                "outwardIssue": {
                    "id": link.get("outwardIssue", {}).get("id", ""),
                    "key": link.get("outwardIssue", {}).get("key", ""),
                    "statusName": link.get("outwardIssue", {}).get("fields", {}).get("status", {}).get("name"),
                    "summary": link.get("outwardIssue", {}).get("fields", {}).get("summary"),
                } if link.get("outwardIssue") else None,
            })

        transformed_subtasks = [
            {
                "id": sub.get("id", ""),
                "key": sub.get("key", ""),
                "summary": sub.get("fields", {}).get("summary", ""),
                "statusName": sub.get("fields", {}).get("status", {}).get("name", ""),
                "issueTypeName": sub.get("fields", {}).get("issuetype", {}).get("name"),
            }
            for sub in subtasks
        ]

        status_category_dict = None
        if status_category:
            status_category_dict = {
                "id": status_category.get("id", ""),
                "key": status_category.get("key", ""),
                "name": status_category.get("name", ""),
                "colorName": status_category.get("colorName", ""),
            }

        priority_dict = None
        if priority:
            priority_dict = {
                "id": priority.get("id", ""),
                "name": priority.get("name", ""),
                "iconUrl": priority.get("iconUrl"),
            }

        resolution_dict = None
        if resolution:
            resolution_dict = {
                "id": resolution.get("id", ""),
                "name": resolution.get("name", ""),
                "description": resolution.get("description"),
            }

        time_tracking_dict = None
        if time_tracking:
            time_tracking_dict = {
                "originalEstimate": time_tracking.get("originalEstimate"),
                "remainingEstimate": time_tracking.get("remainingEstimate"),
                "timeSpent": time_tracking.get("timeSpent"),
                "originalEstimateSeconds": time_tracking.get("originalEstimateSeconds"),
                "remainingEstimateSeconds": time_tracking.get("remainingEstimateSeconds"),
                "timeSpentSeconds": time_tracking.get("timeSpentSeconds"),
            }

        parent_dict = None
        if parent:
            parent_dict = {
                "id": parent.get("id", ""),
                "key": parent.get("key", ""),
                "summary": parent.get("fields", {}).get("summary"),
            }

        votes_dict = None
        if votes:
            votes_dict = {
                "votes": votes.get("votes", 0),
                "hasVoted": votes.get("hasVoted", False),
            }

        watches_dict = None
        if watches:
            watches_dict = {
                "watchCount": watches.get("watchCount", 0),
                "isWatching": watches.get("isWatching", False),
            }

        return {
            "id": data.get("id", ""),
            "issueKey": data.get("key", ""),
            "key": data.get("key", ""),
            "self": data.get("self", ""),
            "summary": fields.get("summary", ""),
            "description": self._extract_adf_text(fields.get("description")),
            "status": {
                "id": status.get("id", ""),
                "name": status.get("name", ""),
                "description": status.get("description"),
                "statusCategory": status_category_dict,
            },
            "issuetype": {
                "id": issue_type.get("id", ""),
                "name": issue_type.get("name", ""),
                "description": issue_type.get("description"),
                "subtask": issue_type.get("subtask", False),
                "iconUrl": issue_type.get("iconUrl"),
            },
            "project": {
                "id": project.get("id", ""),
                "key": project.get("key", ""),
                "name": project.get("name", ""),
                "projectTypeKey": project.get("projectTypeKey"),
            },
            "priority": priority_dict,
            "statusName": status.get("name", ""),
            "assignee": self._transform_user(fields.get("assignee")),
            "assigneeName": fields.get("assignee", {}).get("displayName") or fields.get("assignee", {}).get("accountId"),
            "reporter": self._transform_user(fields.get("reporter")),
            "creator": self._transform_user(fields.get("creator")),
            "labels": fields.get("labels", []),
            "components": transformed_components,
            "fixVersions": transformed_fix_versions,
            "resolution": resolution_dict,
            "duedate": fields.get("duedate"),
            "created": fields.get("created", ""),
            "updated": fields.get("updated", ""),
            "resolutiondate": fields.get("resolutiondate"),
            "timetracking": time_tracking_dict,
            "parent": parent_dict,
            "issuelinks": transformed_issue_links,
            "subtasks": transformed_subtasks,
            "votes": votes_dict,
            "watches": watches_dict,
            "comments": transformed_comments,
            "worklogs": transformed_worklogs,
            "attachments": transformed_attachments,
        }

    async def _get_cloud_id(self, domain: str, access_token: str, headers: dict) -> str:
        url = "https://api.atlassian.com/oauth/token/accessible-resources"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            if response.status_code != 200:
                raise ValueError(f"Failed to get accessible resources ({response.status_code}): {response.text}")
            resources: List[Dict[str, Any]] = response.json()
            normalized_domain = domain.strip().lower().rstrip("/")
            for resource in resources:
                resource_url = resource.get("url", "").strip().lower().rstrip("/")
                if resource_url == f"https://{normalized_domain}" or resource_url.endswith(f"/{normalized_domain}"):
                    return resource["id"]
            available = [r.get("url", "") for r in resources]
            raise ValueError(f"No cloud ID found for domain '{domain}'. Available: {available}")

    async def _fetch_issue(self, cloud_id: str, issue_key: str, headers: dict) -> Dict[str, Any]:
        url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/issue/{issue_key}?expand=renderedFields,names,schema,transitions,operations,editmeta,changelog,versionedRepresentations"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            if response.status_code not in [200]:
                error_msg = response.text
                try:
                    err_data = response.json()
                    error_msg = err_data.get("message") or err_data.get("errorMessages", [None])[0] or error_msg
                except Exception:
                    pass
                raise ValueError(f"Failed to fetch Jira issue ({response.status_code}): {error_msg}")
            return response.json()

    async def _fetch_supplementary(self, cloud_id: str, issue_key: str, headers: dict, data: Dict[str, Any]) -> None:
        base_url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/issue/{issue_key}"
        urls = [
            f"{base_url}/comment?maxResults=100&orderBy=-created",
            f"{base_url}/worklog?maxResults=100",
            f"{base_url}/watchers",
        ]
        async with httpx.AsyncClient(timeout=30.0) as client:
            tasks = [client.get(url, headers=headers) for url in urls]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            # comments
            comments_resp = responses[0]
            if isinstance(comments_resp, httpx.Response) and comments_resp.status_code == 200:
                try:
                    comments_data = comments_resp.json()
                    data["fields"]["comment"] = comments_data.get("comments", [])
                except Exception:
                    pass
            # worklog
            worklog_resp = responses[1]
            if isinstance(worklog_resp, httpx.Response) and worklog_resp.status_code == 200:
                try:
                    worklog_data = worklog_resp.json()
                    data["fields"]["worklog"] = worklog_data
                except Exception:
                    pass
            # watchers
            watchers_resp = responses[2]
            if isinstance(watchers_resp, httpx.Response) and watchers_resp.status_code == 200:
                try:
                    watchers_data = watchers_resp.json()
                    data["fields"]["watches"] = watchers_data
                except Exception:
                    pass

    async def _download_jira_attachments(self, attachments: List[Dict[str, Any]], cloud_id: str, issue_key: str, headers: dict) -> List[Dict[str, Any]]:
        files: List[Dict[str, Any]] = []
        if not attachments:
            return files
        base_url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/issue/{issue_key}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            att_tasks = [client.get(f"{base_url}/attachment/{att['id']}", headers=headers) for att in attachments]
            att_responses = await asyncio.gather(*att_tasks, return_exceptions=True)
            content_tasks = []
            valid_atts: List[Dict[str, Any]] = []
            for i, resp in enumerate(att_responses):
                if isinstance(resp, Exception):
                    continue
                if resp.status_code != 200:
                    continue
                try:
                    att_data = resp.json()
                    content_url = att_data["content"]["links"]["self"]
                    content_tasks.append(client.get(content_url, headers=headers))
                    valid_atts.append(attachments[i])
                except Exception:
                    pass
            if content_tasks:
                content_responses = await asyncio.gather(*content_tasks, return_exceptions=True)
                for j, cont_resp in enumerate(content_responses):
                    if isinstance(cont_resp, Exception):
                        continue
                    if cont_resp.status_code == 200:
                        content = cont_resp.content
                        att = valid_atts[j]
                        b64_data = base64.b64encode(content).decode("utf-8")
                        files.append({
                            "name": att.get("filename", ""),
                            "mimeType": att.get("mimeType", ""),
                            "data": b64_data,
                            "size": len(content),
                        })
        return files

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        domain = parameters["domain"]
        issue_key = parameters["issueKey"]
        include_attachments = parameters.get("includeAttachments", False)
        cloud_id = parameters.get("cloudId")
        try:
            if cloud_id:
                data = await self._fetch_issue(cloud_id, issue_key, headers)
            else:
                cloud_id = await self._get_cloud_id(domain, access_token, headers)
                data = await self._fetch_issue(cloud_id, issue_key, headers)
            await self._fetch_supplementary(cloud_id, issue_key, headers, data)
            issue_data = self._transform_issue_data(data)
            files = []
            if include_attachments and issue_data.get("attachments"):
                files = await self._download_jira_attachments(issue_data["attachments"], cloud_id, issue_key, headers)
            output_data: Dict[str, Any] = {
                "ts": datetime.now(timezone.utc).isoformat(),
                **issue_data,
                "issue": data,
            }
            if files:
                output_data["files"] = files
            output_str = json.dumps(output_data, default=str)
            return ToolResult(success=True, output=output_str, data=output_data)
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")